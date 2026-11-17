from app.email_gateway import EmailMessage, StubEmailGateway


def test_stub_keeps_sent_messages():
    g = StubEmailGateway()
    m = EmailMessage("a@g.rit.edu", "New request", "Ben sent you a request")
    assert g.send(m) is True
    assert g.sent == [m]


def test_stub_can_simulate_unavailable_route():  # SD-1 alternative flow
    g = StubEmailGateway()
    g.available = False
    assert g.send(EmailMessage("a@g.rit.edu", "s", "b")) is False
    assert g.sent == []
