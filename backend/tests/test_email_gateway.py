from app.email_gateway import EmailMessage, HandoffResult, StubEmailGateway


def test_stub_keeps_sent_messages():  # CD-1b StubEmailGateway.sentMessages()
    g = StubEmailGateway()
    m = EmailMessage("a@g.rit.edu", "New request", "Ben sent you a request", notification_id=7)
    assert g.send(m) == HandoffResult.HANDED_OVER
    assert bool(HandoffResult.HANDED_OVER) is True
    assert g.sent_messages() == [m]
    assert m.notification_id == 7  # the message reference quoted in the delivery status (DF-29)


def test_stub_can_simulate_unavailable_route():  # SD-1 M30, M31
    g = StubEmailGateway()
    g.available = False
    result = g.send(EmailMessage("a@g.rit.edu", "s", "b"))
    assert result == HandoffResult.UNAVAILABLE and not result
    assert g.sent_messages() == []


def test_stub_can_print_messages_for_development(capsys):
    g = StubEmailGateway(echo=True)
    g.send(EmailMessage("a@g.rit.edu", "Verify", "link: http://x/verify?token=abc"))
    assert "token=abc" in capsys.readouterr().out


def test_live_gateway_reports_unavailable_when_the_route_is_down():  # SD-1 M30
    from app.email_gateway import EmailMessage, RitEmailGateway
    gw = RitEmailGateway(host="127.0.0.1", port=1, sender="studbud@rit.edu", timeout=1)
    assert gw.send(EmailMessage("a@g.rit.edu", "Subject", "Body")) == HandoffResult.UNAVAILABLE


def test_gateway_is_chosen_by_setting():  # CON-009
    from app.email_gateway import RitEmailGateway, StubEmailGateway, build_gateway
    assert isinstance(build_gateway({"EMAIL_MODE": "stub"}), StubEmailGateway)
    assert isinstance(build_gateway({"EMAIL_MODE": "live"}), StubEmailGateway)  # no SMTP_HOST: stay safe
    assert isinstance(build_gateway({"EMAIL_MODE": "live", "SMTP_HOST": "mail.example"}), RitEmailGateway)
