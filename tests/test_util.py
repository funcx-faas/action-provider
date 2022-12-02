from provider.util import FXUtil

class TestStart:
    def test_check_uuid(self):
        assert FXUtil.check_uuid('587fad41-a393-4456-8de5-ad387461234e')
        assert not FXUtil.check_uuid('87fad41-a393-4456-8de5-ad387461234e')
        assert not FXUtil.check_uuid('')
