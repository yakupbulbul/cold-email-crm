import logging
import base64
import smtplib
import socket
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SMTPDiagnosticResult:
    status: str
    category: str
    message: str
    host: str
    port: int
    security_mode: str
    dns_resolved: bool
    connected: bool
    tls_negotiated: bool
    auth_succeeded: bool


class SMTPProvider(ABC):
    @abstractmethod
    def send_email(self, 
                   host: str, 
                   port: int, 
                   username: str, 
                   password: str, 
                   security_mode: str,
                   sender_email: str,
                   from_header: str,
                   to_emails: List[str], 
                   subject: str, 
                   text_body: str, 
                   html_body: Optional[str] = None,
                   cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None,
                   in_reply_to: Optional[str] = None,
                   references: Optional[str] = None,
                   connect_timeout: int = 5,
                   auth_timeout: int = 10,
                   send_timeout: int = 30) -> tuple[bool, str]:
        pass

    @abstractmethod
    def diagnose_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        security_mode: str,
        connect_timeout: int = 5,
        auth_timeout: int = 10,
    ) -> SMTPDiagnosticResult:
        pass

class MailcowSMTPProvider(SMTPProvider):
    def diagnose_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        security_mode: str,
        connect_timeout: int = 5,
        auth_timeout: int = 10,
    ) -> SMTPDiagnosticResult:
        dns_resolved = False
        connected = False
        tls_negotiated = security_mode == "plain"
        auth_succeeded = False
        normalized_mode = (security_mode or "").strip().lower() or ("ssl" if port == 465 else "starttls")
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            dns_resolved = True
        except socket.gaierror:
            return SMTPDiagnosticResult(
                status="failed",
                category="dns_resolution_failed",
                message="SMTP host could not be resolved from the backend environment.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=False,
                connected=False,
                tls_negotiated=False,
                auth_succeeded=False,
            )

        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if normalized_mode == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=connect_timeout, context=ssl.create_default_context())
                connected = True
                tls_negotiated = True
            else:
                server = smtplib.SMTP(host, port, timeout=connect_timeout)
                connected = True
                server.ehlo()
                if normalized_mode == "starttls":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    tls_negotiated = True

            if getattr(server, "sock", None):
                server.sock.settimeout(auth_timeout)
            server.login(username, password)
            auth_succeeded = True
            return SMTPDiagnosticResult(
                status="healthy",
                category="ok",
                message="SMTP host accepted the connection, negotiated the expected security mode, and authenticated successfully.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=auth_succeeded,
            )
        except socket.timeout:
            category = "connect_timeout" if not connected else "auth_timeout"
            message = "SMTP server timed out before the connection could be completed." if not connected else "SMTP server timed out during authentication."
            return SMTPDiagnosticResult(
                status="failed",
                category=category,
                message=message,
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=auth_succeeded,
            )
        except ssl.SSLError:
            return SMTPDiagnosticResult(
                status="failed",
                category="tls_failed",
                message="SMTP TLS negotiation failed for the selected security mode.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=False,
                auth_succeeded=False,
            )
        except smtplib.SMTPAuthenticationError:
            return SMTPDiagnosticResult(
                status="failed",
                category="auth_failed",
                message="SMTP rejected the mailbox credentials.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=False,
            )
        except (ConnectionRefusedError, OSError):
            return SMTPDiagnosticResult(
                status="failed",
                category="connect_failed",
                message="SMTP server is unreachable from the backend environment.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=False,
                tls_negotiated=False,
                auth_succeeded=False,
            )
        except smtplib.SMTPException:
            return SMTPDiagnosticResult(
                status="failed",
                category="smtp_handshake_failed",
                message="SMTP server rejected the connection or handshake before authentication completed.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=False,
            )
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass

    def send_email(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        security_mode: str,
        sender_email: str,
        from_header: str,
        to_emails: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        connect_timeout: int = 5,
        auth_timeout: int = 10,
        send_timeout: int = 30,
    ) -> tuple[bool, str]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = ", ".join(to_emails)
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        if not msg.get("Message-ID"):
            sender_domain = (sender_email.rsplit("@", 1)[1].strip() if "@" in sender_email else "").strip() or None
            msg["Message-ID"] = make_msgid(domain=sender_domain)

        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        normalized_mode = (security_mode or "").strip().lower() or ("ssl" if port == 465 else "starttls")
        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if normalized_mode == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=connect_timeout, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(host, port, timeout=connect_timeout)
                server.ehlo()
                if normalized_mode == "starttls":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()

            if getattr(server, "sock", None):
                server.sock.settimeout(auth_timeout)
            server.login(username, password)

            if getattr(server, "sock", None):
                server.sock.settimeout(send_timeout)
            all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])
            server.send_message(msg, from_addr=sender_email, to_addrs=all_recipients)
            return True, msg.get("Message-ID", "unknown-id")
        except socket.gaierror:
            logger.error("SMTP Error: dns resolution failed for %s:%s", host, port)
            return False, "dns resolution failed"
        except socket.timeout:
            logger.error("SMTP Error: timed out for %s:%s", host, port)
            return False, "timed out"
        except ssl.SSLError:
            logger.error("SMTP Error: tls negotiation failed for %s:%s", host, port)
            return False, "tls negotiation failed"
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Error: authentication failed for %s", username)
            return False, "authentication failed"
        except smtplib.SMTPRecipientsRefused:
            logger.error("SMTP Error: recipient refused for %s", to_emails)
            return False, "recipient refused"
        except (ConnectionRefusedError, OSError):
            logger.error("SMTP Error: server unreachable for %s:%s", host, port)
            return False, "connection failed"
        except Exception as e:
            logger.error(f"SMTP Error: {str(e)}")
            return False, str(e)
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass


class GoogleWorkspaceSMTPProvider:
    def _xoauth2_string(self, username: str, access_token: str) -> str:
        payload = f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
        return base64.b64encode(payload).decode("ascii")

    def diagnose_connection(
        self,
        host: str,
        port: int,
        username: str,
        access_token: str,
        security_mode: str,
        connect_timeout: int = 5,
        auth_timeout: int = 10,
    ) -> SMTPDiagnosticResult:
        dns_resolved = False
        connected = False
        tls_negotiated = security_mode == "plain"
        auth_succeeded = False
        normalized_mode = (security_mode or "").strip().lower() or ("ssl" if port == 465 else "starttls")
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            dns_resolved = True
        except socket.gaierror:
            return SMTPDiagnosticResult(
                status="failed",
                category="dns_resolution_failed",
                message="SMTP host could not be resolved from the backend environment.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=False,
                connected=False,
                tls_negotiated=False,
                auth_succeeded=False,
            )

        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if normalized_mode == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=connect_timeout, context=ssl.create_default_context())
                connected = True
                tls_negotiated = True
            else:
                server = smtplib.SMTP(host, port, timeout=connect_timeout)
                connected = True
                server.ehlo()
                if normalized_mode == "starttls":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    tls_negotiated = True

            if getattr(server, "sock", None):
                server.sock.settimeout(auth_timeout)
            code, response = server.docmd("AUTH", f"XOAUTH2 {self._xoauth2_string(username, access_token)}")
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, response)
            auth_succeeded = True
            return SMTPDiagnosticResult(
                status="healthy",
                category="ok",
                message="Google Workspace SMTP accepted XOAUTH2 authentication successfully.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=auth_succeeded,
            )
        except socket.timeout:
            category = "connect_timeout" if not connected else "auth_timeout"
            message = "SMTP server timed out before the connection could be completed." if not connected else "SMTP server timed out during XOAUTH2 authentication."
            return SMTPDiagnosticResult(
                status="failed",
                category=category,
                message=message,
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=auth_succeeded,
            )
        except ssl.SSLError:
            return SMTPDiagnosticResult(
                status="failed",
                category="tls_failed",
                message="SMTP TLS negotiation failed for the selected security mode.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=False,
                auth_succeeded=False,
            )
        except smtplib.SMTPAuthenticationError:
            return SMTPDiagnosticResult(
                status="failed",
                category="auth_failed",
                message="Google Workspace rejected the OAuth token for SMTP.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=False,
            )
        except (ConnectionRefusedError, OSError):
            return SMTPDiagnosticResult(
                status="failed",
                category="connect_failed",
                message="SMTP server is unreachable from the backend environment.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=False,
                tls_negotiated=False,
                auth_succeeded=False,
            )
        except smtplib.SMTPException:
            return SMTPDiagnosticResult(
                status="failed",
                category="smtp_handshake_failed",
                message="SMTP server rejected XOAUTH2 before the connection completed.",
                host=host,
                port=port,
                security_mode=normalized_mode,
                dns_resolved=dns_resolved,
                connected=connected,
                tls_negotiated=tls_negotiated,
                auth_succeeded=False,
            )
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass

    def send_email(
        self,
        host: str,
        port: int,
        username: str,
        access_token: str,
        security_mode: str,
        sender_email: str,
        from_header: str,
        to_emails: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        connect_timeout: int = 5,
        auth_timeout: int = 10,
        send_timeout: int = 30,
    ) -> tuple[bool, str]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = ", ".join(to_emails)
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        if not msg.get("Message-ID"):
            sender_domain = (sender_email.rsplit("@", 1)[1].strip() if "@" in sender_email else "").strip() or None
            msg["Message-ID"] = make_msgid(domain=sender_domain)

        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        normalized_mode = (security_mode or "").strip().lower() or ("ssl" if port == 465 else "starttls")
        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if normalized_mode == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=connect_timeout, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(host, port, timeout=connect_timeout)
                server.ehlo()
                if normalized_mode == "starttls":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()

            if getattr(server, "sock", None):
                server.sock.settimeout(auth_timeout)
            code, response = server.docmd("AUTH", f"XOAUTH2 {self._xoauth2_string(username, access_token)}")
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, response)

            if getattr(server, "sock", None):
                server.sock.settimeout(send_timeout)
            all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])
            server.send_message(msg, from_addr=sender_email, to_addrs=all_recipients)
            return True, msg.get("Message-ID", "unknown-id")
        except socket.gaierror:
            logger.error("Google SMTP Error: dns resolution failed for %s:%s", host, port)
            return False, "dns resolution failed"
        except socket.timeout:
            logger.error("Google SMTP Error: timed out for %s:%s", host, port)
            return False, "timed out"
        except ssl.SSLError:
            logger.error("Google SMTP Error: tls negotiation failed for %s:%s", host, port)
            return False, "tls negotiation failed"
        except smtplib.SMTPAuthenticationError:
            logger.error("Google SMTP Error: xoauth2 authentication failed for %s", username)
            return False, "authentication failed"
        except smtplib.SMTPRecipientsRefused:
            logger.error("Google SMTP Error: recipient refused for %s", to_emails)
            return False, "recipient refused"
        except (ConnectionRefusedError, OSError):
            logger.error("Google SMTP Error: server unreachable for %s:%s", host, port)
            return False, "connection failed"
        except Exception as e:
            logger.error(f"Google SMTP Error: {e}")
            return False, str(e)
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass
