"""Intended-account preflight checks with scripted OANDA practice responses."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from io import StringIO
import json
from unittest.mock import patch
from urllib.parse import urlencode

from nnfx_practice.broker import HTTPReply, PRACTICE_HOST, PracticeBroker
from nnfx_practice.config import ConfigurationError, load_account_binding
from nnfx_practice.preflight import PERMITTED_PAIRS, check_account, check_candles, main
from tests.support import ACCOUNT, TOKEN, Call, NotebookCase, ScriptedTransport
from tests.test_m03 import daily_body


_ROOT = f"/v3/accounts/{ACCOUNT}"
_NAMES = tuple(pair.replace("-", "_") for pair in PERMITTED_PAIRS)
_INSTRUMENTS = Call("GET", _ROOT + "/instruments?" + urlencode({"instruments": ",".join(_NAMES)}))
_PRICING = Call("GET", _ROOT + "/pricing?" + urlencode({
    "instruments": ",".join(_NAMES), "includeHomeConversions": "true",
}))
_PROFILE = {
    "division": "OANDA Corporation", "profile_reference": "fixture-portal-reference", "platform": "mt4-associated",
}
_PRICE_TIME = "2026-11-16T21:49:59.123456789Z"


def account_body(home="USD"):
    return {"lastTransactionID": "100", "account": {
        "id": ACCOUNT, "currency": home, "balance": "1000.00", "marginAvailable": "960.21",
        "openTradeCount": 1, "pendingOrderCount": 1, "hedgingEnabled": False,
        "guaranteedStopLossOrderMode": "DISABLED", "alias": f"Bearer {TOKEN}",
        "trades": [{"id": "91", "instrument": "EUR_USD", "state": "OPEN"}],
        "orders": [{"id": "92", "tradeID": "91", "type": "STOP_LOSS", "state": "PENDING"}],
    }}


def instruments_body():
    return {"instruments": [{
        "name": name, "type": "CURRENCY", "displayPrecision": 3 if name.endswith("JPY") else 5,
        "pipLocation": -2 if name.endswith("JPY") else -4, "tradeUnitsPrecision": 0,
        "minimumTradeSize": "1", "maximumOrderUnits": "100000000",
        "maximumPositionSize": "0", "marginRate": "0.05",
        "guaranteedStopLossOrderMode": "DISABLED",
    } for name in _NAMES]}


def pricing_body(home="USD"):
    currencies = sorted({currency for name in _NAMES for currency in name.split("_")})
    return {"time": _PRICE_TIME, "prices": [{
        "instrument": name, "time": _PRICE_TIME, "tradeable": True,
        "bids": [{"price": "1.02", "liquidity": 100}], "asks": [{"price": "1.03", "liquidity": 100}],
    } for name in _NAMES], "homeConversions": [{
        "currency": currency, "accountLoss": "1.00000000" if currency == home else "0.89",
        "accountGain": "1.01", "positionValue": "0.90",
    } for currency in currencies]}


def candle_call(name):
    params = ("price=M&granularity=D&count=50&smooth=false"
              "&dailyAlignment=17&alignmentTimezone=America%2FNew_York")
    return Call("GET", f"{_ROOT}/instruments/{name}/candles?{params}")


class PreflightChecks(NotebookCase):
    def broker(self, *steps, binding=None):
        transport = ScriptedTransport(*steps)
        self.addCleanup(transport.assert_consumed)
        return PracticeBroker(binding if binding is not None else self.binding(),
                              transport=transport, now=self.clock.now)

    def account_run(self, home="USD", *, account=None, instruments=None, pricing=None, profile=_PROFILE):
        self.write_private(currency=home)
        binding = load_account_binding(self.root, "controller-a")
        broker = self.broker(
            (Call("GET", _ROOT), HTTPReply(200, account if account is not None else account_body(home))),
            (_INSTRUMENTS, HTTPReply(200, instruments if instruments is not None else instruments_body())),
            (_PRICING, HTTPReply(200, pricing if pricing is not None else pricing_body(home), "price-request")),
            binding=binding,
        )
        return check_account(broker, **profile)

    def test_a05_a16_account_preflight_without_strategy_and_redacted_evidence(self):
        self.manifest_path.unlink()
        path = self.root / ".env"
        path.write_text(path.read_text().replace("PRACTICE_A_LOOKBACK_CANDLES=50\n", ""))
        binding = load_account_binding(self.root, "controller-a")
        with self.assertRaises(ConfigurationError):
            self.binding()
        broker = self.broker(
            (Call("GET", _ROOT), HTTPReply(200, account_body())),
            (_INSTRUMENTS, HTTPReply(200, instruments_body())),
            (_PRICING, HTTPReply(200, pricing_body(), f"fixture-{ACCOUNT}")),
            binding=binding,
        )
        report = check_account(broker, **_PROFILE)
        self.assertEqual((report["source"], report["host"], report["status"]),
                         ("fixture", PRACTICE_HOST, "passed"))
        body = report["account"]["evidence"]["body"]["account"]
        self.assertEqual((body["balance"], body["currency"]), ("1000.00", "USD"))
        self.assertEqual([body["trades"][0]["id"], body["orders"][0]["id"]], ["91", "92"])
        self.assertEqual(report["division"]["reference"], _PROFILE["profile_reference"])
        review = report["execution_review"]
        self.assertTrue(review["existing_activity"])
        self.assertFalse(review["hedging_enabled"])
        self.assertIn("Avoid on MT4", review["client_extensions"])
        self.assertIn("unique sizes", review["protected_trade_sizes"])
        self.assertEqual(list(report["instruments"]["pairs"]), list(PERMITTED_PAIRS))
        prices = report["pricing"]
        self.assertEqual(list(prices["pairs"]), list(PERMITTED_PAIRS))
        self.assertEqual(len(prices["pairs"]), 28)
        self.assertIn("includeHomeConversions=true", prices["evidence"]["path"])
        self.assertEqual(prices["pairs"]["EUR-USD"]["quote_loss"]["accountLoss"], "1.00000000")
        self.assertEqual(prices["pairs"]["USD-JPY"]["quote_loss"]["accountLoss"], "0.89")
        self.assertEqual(prices["pairs"]["EUR-USD"]["tradeability"]["price_time"], _PRICE_TIME)
        self.assertEqual(len(prices["matching_quote"]["pairs"]), 4)
        self.assertEqual(prices["home_identity"]["validation"], "valid")
        evidence = json.dumps(report, allow_nan=False)
        self.assertNotIn(ACCOUNT, evidence)
        self.assertNotIn(TOKEN, evidence)
        self.assertFalse((self.root / "var").exists())

    def test_a05_base_only_and_absent_home_currency_applicability(self):
        eur = self.account_run("EUR")["pricing"]
        self.assertEqual(eur["matching_quote"]["validation"], "not_applicable")
        self.assertIn("No permitted pair", eur["matching_quote"]["reason"])
        self.assertIn("EUR-USD", eur["home_identity"]["pairs"])
        self.assertEqual(eur["home_identity"]["accountLoss"], "1.00000000")
        self.assertEqual(eur["pairs"]["EUR-USD"]["quote_loss"]["currency"], "USD")
        self.assertEqual(eur["pairs"]["EUR-USD"]["quote_loss"]["accountLoss"], "0.89")
        sgd = self.account_run("SGD")
        self.assertEqual(sgd["status"], "passed")
        for case in ("matching_quote", "home_identity"):
            self.assertEqual(sgd["pricing"][case]["validation"], "not_applicable")
            self.assertEqual(sgd["pricing"][case]["currency"], "SGD")
            self.assertTrue(sgd["pricing"][case]["reason"])

    def test_a05_required_quote_account_loss_has_no_fallback(self):
        for currency, pair in (("USD", "EUR-USD"), ("JPY", "USD-JPY")):
            for factor in (None, "0", "-1", "NaN", "Infinity", "abc", 1):
                with self.subTest(currency=currency, factor=factor):
                    body = pricing_body()
                    row = next(row for row in body["homeConversions"] if row["currency"] == currency)
                    if factor is None:
                        row.pop("accountLoss")
                    else:
                        row["accountLoss"] = factor
                    report = self.account_run(pricing=body)
                    self.assertEqual(report["status"], "incomplete")
                    self.assertEqual(report["pricing"]["pairs"][pair]["quote_loss"]["validation"], "unavailable")

            body = pricing_body()
            body["homeConversions"] = [row for row in body["homeConversions"] if row["currency"] != currency]
            report = self.account_run(pricing=body)
            self.assertEqual(report["pricing"]["pairs"][pair]["quote_loss"]["validation"], "unavailable")

    def test_a05_non_identity_and_ambiguous_conversions_fail(self):
        for home in ("USD", "EUR"):
            with self.subTest(home=home):
                body = pricing_body(home)
                next(row for row in body["homeConversions"] if row["currency"] == home)["accountLoss"] = "1.00000001"
                report = self.account_run(home, pricing=body)
                self.assertEqual(report["status"], "incomplete")
                self.assertIn("equal 1", report["pricing"]["home_identity"]["reason"])
        body = pricing_body()
        body["homeConversions"].append(body["homeConversions"][0].copy())
        report = self.account_run(pricing=body)
        self.assertEqual(report["pricing"]["pairs"]["EUR-AUD"]["quote_loss"]["validation"], "unavailable")

    def test_a05_a13_missing_metadata_and_untradeable_prices_are_visible_per_pair(self):
        metadata = instruments_body()
        metadata["instruments"].pop()
        metadata["instruments"][0]["displayPrecision"] = True
        metadata["instruments"][1]["minimumTradeSize"] = "0"
        metadata["instruments"][2]["marginRate"] = "NaN"
        body = pricing_body()
        body["prices"][0].update(tradeable=False, status="tradeable")
        body["prices"][1]["asks"] = []
        body["prices"][2].pop("tradeable")
        body["prices"][2]["status"] = "tradeable"
        report = self.account_run(instruments=metadata, pricing=body)
        self.assertEqual(report["status"], "incomplete")
        for pair in (*PERMITTED_PAIRS[:3], "NZD-CAD"):
            self.assertTrue(report["instruments"]["pairs"][pair]["reason"])
        checks = report["pricing"]["pairs"]
        self.assertIn("untradeable", checks["EUR-USD"]["tradeability"]["reason"])
        self.assertIn("asks", checks["GBP-USD"]["tradeability"]["reason"])
        self.assertEqual(checks["AUD-USD"]["tradeability"]["validation"], "valid")
        self.assertEqual(checks["EUR-USD"]["quote_loss"]["accountLoss"], "1.00000000")

    def test_a16_wrong_identity_and_currency_stop_before_market_reads(self):
        for field, value in (("id", "different-private-account"), ("currency", "EUR")):
            with self.subTest(field=field):
                wrong = account_body()
                wrong["account"][field] = value
                broker = self.broker((Call("GET", _ROOT), HTTPReply(200, wrong)))
                report = check_account(broker)
                self.assertEqual(report["status"], "incomplete")
                self.assertIn("differs", report["account"]["reason"])
                self.assertNotIn("different-private-account", json.dumps(report))
                self.assertNotIn("pricing", report)

    def test_a16_incomplete_activity_and_unknown_division_remain_visible(self):
        body = account_body()
        body["account"]["pendingOrderCount"] = 2
        report = self.account_run(account=body, profile={})
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("orders do not match", report["account"]["reason"])
        self.assertEqual(report["division"]["validation"], "unavailable")
        self.assertEqual(report["execution_review"]["platform"], "unconfirmed")
        self.assertEqual(report["pricing"]["validation"], "valid")

    def test_cli_runs_account_phase_and_requires_manifest_for_candles(self):
        self.manifest_path.unlink()
        account_binding = load_account_binding(self.root, "controller-a")
        broker = self.broker(
            (Call("GET", _ROOT), HTTPReply(200, account_body())),
            (_INSTRUMENTS, HTTPReply(200, instruments_body())),
            (_PRICING, HTTPReply(200, pricing_body())),
            binding=account_binding,
        )
        with (patch("nnfx_practice.preflight.Path.cwd", return_value=self.root),
              patch("nnfx_practice.preflight.PracticeBroker", return_value=broker) as factory,
              redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()) as stderr):
            self.assertEqual(main(["controller-a", "--division", _PROFILE["division"],
                                   "--profile-reference", _PROFILE["profile_reference"]]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["source"], "fixture")
            with self.assertRaises(SystemExit) as failure:
                main(["controller-a", "--candles"])
            self.assertEqual(failure.exception.code, 2)
            self.assertIn("strategy manifest", stderr.getvalue())
            factory.assert_called_once_with(account_binding)

    def test_a01_a03_qualified_count_for_all_pairs_at_1650_across_dst(self):
        for stamp in ("2026-11-16T21:50:00Z", "2026-03-09T20:50:00Z"):
            with self.subTest(stamp=stamp):
                self.clock.current = datetime.fromisoformat(stamp)
                session = date.fromisoformat(stamp[:10])
                steps = [(Call("GET", _ROOT), HTTPReply(200, account_body()))]
                for name in _NAMES:
                    steps.append((candle_call(name), HTTPReply(200, {**daily_body(session), "instrument": name})))
                broker = self.broker(*steps)
                report = check_candles(broker)
                self.assertEqual((report["source"], report["status"]), ("fixture", "passed"))
                self.assertEqual(report["manifest_sha256"], broker.binding.manifest.hash)
                self.assertEqual(report["lookback_candles"], 50)
                self.assertEqual(report["session_date"], session.isoformat())
                self.assertEqual(report["valid_windows"], 28)
                for pair in report["pairs"].values():
                    self.assertEqual(pair["received_count"], 50)
                    self.assertEqual(pair["responded_at"], stamp.replace("Z", ".000000Z"))
                self.assertNotIn('"candles": [', json.dumps(report))

    def test_a01_a03_a13_unqualified_or_missed_launch_makes_no_request(self):
        account = load_account_binding(self.root, "controller-a")
        report = check_candles(self.broker(binding=account))
        self.assertIn("qualified M03 manifest", report["reason"])
        for stamp in ("2026-11-16T21:49:59Z", "2026-11-16T21:51:00Z", "2026-11-21T21:50:00Z"):
            with self.subTest(stamp=stamp):
                self.clock.current = datetime.fromisoformat(stamp)
                report = check_candles(self.broker())
                self.assertEqual(report["status"], "incomplete")
                self.assertIn("weekday 16:50", report["reason"])

    def test_a01_a03_a13_unavailable_windows_and_rollover_have_distinct_evidence(self):
        session = date(2026, 11, 16)
        steps = [
            (Call("GET", _ROOT), HTTPReply(200, account_body())),
            (candle_call("EUR_USD"), HTTPReply(200, daily_body(session, count=49), "short-window")),
            (candle_call("GBP_USD"), HTTPReply(503, {"errorMessage": TOKEN}, "market-unavailable")),
        ]

        def before_rollover():
            self.clock.advance(599)
            return HTTPReply(200, {**daily_body(session), "instrument": "AUD_USD"}, "last-valid")

        def at_rollover():
            self.clock.advance(1)
            return HTTPReply(200, {**daily_body(session), "instrument": "NZD_USD"}, "late")

        steps.extend([(candle_call("AUD_USD"), before_rollover), (candle_call("NZD_USD"), at_rollover)])
        report = check_candles(self.broker(*steps))
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["valid_windows"], 1)
        self.assertEqual(len(report["pairs"]), 28)
        short = report["pairs"]["EUR-USD"]
        self.assertEqual((short["received_count"], short["request_id"]), (49, "short-window"))
        self.assertEqual(report["pairs"]["GBP-USD"]["http_status"], 503)
        self.assertEqual(report["pairs"]["AUD-USD"]["responded_at"], "2026-11-16T21:59:59.000000Z")
        late = report["pairs"]["NZD-USD"]
        self.assertEqual(late["responded_at"], "2026-11-16T22:00:00.000000Z")
        self.assertIn("outside the intended session", late["reason"])
        skipped = report["pairs"]["USD-CHF"]
        self.assertIsNone(skipped["requested_at"])
        self.assertIn("Rollover reached", skipped["reason"])
        self.assertNotIn(TOKEN, json.dumps(report))
