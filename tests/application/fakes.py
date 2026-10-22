from copy import deepcopy
from dataclasses import replace


class MemoryRepository:
    def __init__(self):
        self.rows = {}

    def list(self):
        return list(self.rows.values())

    def get(self, item_id):
        return self.rows.get(item_id)

    def save(self, item):
        saved = replace(item, id=item.id or max(self.rows, default=0) + 1)
        self.rows[saved.id] = saved
        return saved


class MemoryUnitOfWork:
    names = ('festivals', 'artists', 'stages', 'concerts', 'incidents')

    def __init__(self):
        for name in self.names:
            setattr(self, name, MemoryRepository())
        self.commits = 0
        self.fail_commit = False
        self.in_transaction = False

    def __enter__(self):
        self.snapshot = {name: deepcopy(getattr(self, name).rows) for name in self.names}
        self.committed = False
        self.in_transaction = True
        return self

    def commit(self):
        if self.fail_commit:
            raise RuntimeError('Storage unavailable')
        self.commits += 1
        self.committed = True

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.committed:
            for name, rows in self.snapshot.items():
                getattr(self, name).rows = rows
        self.in_transaction = False


class RecordingNotifier:
    def __init__(self, uow):
        self.uow = uow
        self.events = []
        self.fail = False

    def notify(self, event):
        assert not self.uow.in_transaction
        assert self.uow.commits > 0
        if self.fail:
            raise RuntimeError('Notification unavailable')
        self.events.append(event)
