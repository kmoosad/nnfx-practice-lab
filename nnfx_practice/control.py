"""One local exclusion boundary for launches and notebook maintenance.

Never remove the lock file (its inode is shared). The systemd adapter masks the
service while maintenance holds this exclusion.
"""

from contextlib import contextmanager
import fcntl
import os


class MaintenanceDeferred(RuntimeError):
    pass


@contextmanager
def controller_exclusion(root, binding):
    path = binding.experiment.notebook_path(root).with_suffix('.lock')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise MaintenanceDeferred('Controller or notebook maintenance is already active') from None
        yield
    finally:
        os.close(descriptor)


@contextmanager
def maintenance(root, binding, service):
    """Require pause_timer/timer_active/service_active/launch_pending/restore_timer.

    All controller invocations use the same exclusion. The adapter prevents
    external service launches too.
    Callers close the notebook before leaving this context, including on failure.
    """
    with controller_exclusion(root, binding):
        prior = service.timer_active()
        try:
            service.pause_timer()
            if service.timer_active() or service.service_active() or service.launch_pending():
                raise MaintenanceDeferred('Maintenance requires a paused timer and inactive service with no pending launch')
            yield
        finally:
            # Callers have closed/released the notebook. Retain local exclusion
            # during restoration so a second maintenance cannot race the unmask.
            service.restore_timer(prior)
