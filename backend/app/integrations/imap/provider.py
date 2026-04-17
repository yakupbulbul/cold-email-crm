import email.utils
import base64
import imaplib
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass
class IMAPFetchedMessage:
    uid: str
    raw_bytes: bytes
    is_read: bool
    received_at: object | None


@dataclass
class IMAPConnectionResult:
    status: str
    category: str
    message: str


class IMAPProviderError(Exception):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category
        self.message = message


class MailcowIMAPProvider:
    uid_pattern = re.compile(r"UID (\d+)")

    def diagnose_connection(self, host: str, port: int, username: str, password: str, timeout: int = 8) -> IMAPConnectionResult:
        mail = None
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            mail = imaplib.IMAP4_SSL(host, port, timeout=timeout)
            mail.login(username, password)
            mail.select("INBOX", readonly=True)
            return IMAPConnectionResult(status="healthy", category="ok", message="IMAP connection and authentication succeeded.")
        except socket.gaierror:
            return IMAPConnectionResult(status="failed", category="dns_resolution_failed", message="IMAP host could not be resolved.")
        except socket.timeout:
            return IMAPConnectionResult(status="failed", category="timeout", message="IMAP server timed out during connection.")
        except imaplib.IMAP4.error as exc:
            return IMAPConnectionResult(status="failed", category="auth_failed", message=f"IMAP authentication failed: {exc}")
        except OSError as exc:
            return IMAPConnectionResult(status="failed", category="connect_failed", message=f"IMAP server is unreachable: {exc}")
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass

    def fetch_messages(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        *,
        since_uid: str | None = None,
        limit: int = 100,
        timeout: int = 8,
    ) -> list[IMAPFetchedMessage]:
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(host, port, timeout=timeout)
            mail.login(username, password)
            status, _ = mail.select("INBOX", readonly=True)
            if status != "OK":
                raise IMAPProviderError("select_failed", "IMAP inbox could not be selected.")

            status, data = mail.uid("search", None, "ALL")
            if status != "OK":
                raise IMAPProviderError("search_failed", "IMAP inbox search failed.")

            all_uids = [uid.decode() for uid in data[0].split() if uid]
            candidate_uids = [uid for uid in all_uids if int(uid) > int(since_uid)] if since_uid else all_uids[-limit:]

            fetched: list[IMAPFetchedMessage] = []
            for uid in candidate_uids:
                status, msg_data = mail.uid("fetch", uid, "(RFC822 FLAGS INTERNALDATE UID)")
                if status != "OK":
                    continue
                raw_bytes = b""
                flags: tuple[bytes, ...] = ()
                received_at = None
                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
                    header_bytes, payload = response_part
                    raw_bytes = payload or b""
                    flags = tuple(imaplib.ParseFlags(header_bytes))
                    internal_date = imaplib.Internaldate2tuple(header_bytes)
                    if internal_date is not None:
                        received_at = datetime(*internal_date[:6])
                if not raw_bytes:
                    continue
                fetched.append(
                    IMAPFetchedMessage(
                        uid=uid,
                        raw_bytes=raw_bytes,
                        is_read=b"\\Seen" in flags,
                        received_at=received_at,
                    )
                )

            return fetched
        except IMAPProviderError:
            raise
        except socket.gaierror as exc:
            raise IMAPProviderError("dns_resolution_failed", f"IMAP host could not be resolved: {exc}") from exc
        except socket.timeout as exc:
            raise IMAPProviderError("timeout", f"IMAP server timed out during fetch: {exc}") from exc
        except imaplib.IMAP4.error as exc:
            raise IMAPProviderError("auth_failed", f"IMAP authentication failed: {exc}") from exc
        except OSError as exc:
            raise IMAPProviderError("connect_failed", f"IMAP server is unreachable: {exc}") from exc
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass


class GoogleWorkspaceIMAPProvider:
    uid_pattern = re.compile(r"UID (\d+)")

    def _xoauth2_string(self, username: str, access_token: str) -> str:
        payload = f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
        return base64.b64encode(payload).decode("ascii")

    def diagnose_connection(self, host: str, port: int, username: str, access_token: str, timeout: int = 8) -> IMAPConnectionResult:
        mail = None
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            mail = imaplib.IMAP4_SSL(host, port, timeout=timeout)
            code, _ = mail.authenticate("XOAUTH2", lambda _: self._xoauth2_string(username, access_token).encode("ascii"))
            if code != "OK":
                raise imaplib.IMAP4.error("Google Workspace XOAUTH2 authentication failed.")
            mail.select("INBOX", readonly=True)
            return IMAPConnectionResult(status="healthy", category="ok", message="Google Workspace IMAP connection and authentication succeeded.")
        except socket.gaierror:
            return IMAPConnectionResult(status="failed", category="dns_resolution_failed", message="IMAP host could not be resolved.")
        except socket.timeout:
            return IMAPConnectionResult(status="failed", category="timeout", message="IMAP server timed out during connection.")
        except imaplib.IMAP4.error as exc:
            return IMAPConnectionResult(status="failed", category="auth_failed", message=f"IMAP authentication failed: {exc}")
        except OSError as exc:
            return IMAPConnectionResult(status="failed", category="connect_failed", message=f"IMAP server is unreachable: {exc}")
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass

    def fetch_messages(
        self,
        host: str,
        port: int,
        username: str,
        access_token: str,
        *,
        since_uid: str | None = None,
        limit: int = 100,
        timeout: int = 8,
    ) -> list[IMAPFetchedMessage]:
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(host, port, timeout=timeout)
            code, _ = mail.authenticate("XOAUTH2", lambda _: self._xoauth2_string(username, access_token).encode("ascii"))
            if code != "OK":
                raise IMAPProviderError("auth_failed", "Google Workspace rejected the OAuth token for IMAP.")
            status, _ = mail.select("INBOX", readonly=True)
            if status != "OK":
                raise IMAPProviderError("select_failed", "IMAP inbox could not be selected.")

            status, data = mail.uid("search", None, "ALL")
            if status != "OK":
                raise IMAPProviderError("search_failed", "IMAP inbox search failed.")

            all_uids = [uid.decode() for uid in data[0].split() if uid]
            candidate_uids = [uid for uid in all_uids if int(uid) > int(since_uid)] if since_uid else all_uids[-limit:]

            fetched: list[IMAPFetchedMessage] = []
            for uid in candidate_uids:
                status, msg_data = mail.uid("fetch", uid, "(RFC822 FLAGS INTERNALDATE UID)")
                if status != "OK":
                    continue
                raw_bytes = b""
                flags: tuple[bytes, ...] = ()
                received_at = None
                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
                    header_bytes, payload = response_part
                    raw_bytes = payload or b""
                    flags = tuple(imaplib.ParseFlags(header_bytes))
                    internal_date = imaplib.Internaldate2tuple(header_bytes)
                    if internal_date is not None:
                        received_at = datetime(*internal_date[:6])
                if not raw_bytes:
                    continue
                fetched.append(
                    IMAPFetchedMessage(
                        uid=uid,
                        raw_bytes=raw_bytes,
                        is_read=b"\\Seen" in flags,
                        received_at=received_at,
                    )
                )
            return fetched
        except IMAPProviderError:
            raise
        except socket.gaierror as exc:
            raise IMAPProviderError("dns_resolution_failed", f"IMAP host could not be resolved: {exc}") from exc
        except socket.timeout as exc:
            raise IMAPProviderError("timeout", f"IMAP server timed out during fetch: {exc}") from exc
        except imaplib.IMAP4.error as exc:
            raise IMAPProviderError("auth_failed", f"IMAP authentication failed: {exc}") from exc
        except OSError as exc:
            raise IMAPProviderError("connect_failed", f"IMAP server is unreachable: {exc}") from exc
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass
