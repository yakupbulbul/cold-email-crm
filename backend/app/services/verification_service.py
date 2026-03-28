import re
import dns.resolver
from sqlalchemy.orm import Session
from app.models.verification import EmailVerificationLog

class EmailVerificationService:
    DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com"}
    ROLE_PREFIXES = {"admin", "info", "sales", "support", "contact", "billing", "marketing"}

    def __init__(self, db: Session):
        self.db = db

    def verify_email(self, email: str, contact_id: str = None) -> EmailVerificationLog:
        email = email.strip().lower()
        log = EmailVerificationLog(email=email, contact_id=contact_id)
        
        # 1. Syntax Check
        email_regex = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
        if not email_regex.match(email):
            log.syntax_valid = False
            log.final_status = "invalid"
            return self._save_log(log)
            
        log.syntax_valid = True
        domain = email.split("@")[1]
        local_part = email.split("@")[0]
        
        # 2. Disposable Check
        if domain in self.DISPOSABLE_DOMAINS:
            log.disposable = True
            log.final_status = "disposable"
            return self._save_log(log)
            
        # 3. Role-based Check
        if local_part in self.ROLE_PREFIXES:
            log.role_based = True
            log.final_status = "role_based"
            return self._save_log(log)
            
        # 4. Domain / MX Check
        try:
            records = dns.resolver.resolve(domain, 'MX')
            if len(records) > 0:
                log.domain_valid = True
                log.mx_valid = True
            else:
                log.final_status = "no_mx"
                return self._save_log(log)
        except Exception:
            log.domain_valid = False
            log.mx_valid = False
            log.final_status = "invalid"
            return self._save_log(log)
            
        # Calculation for Score
        score = 0
        if log.syntax_valid: score += 20
        if log.domain_valid: score += 20
        if log.mx_valid: score += 40
        if not log.disposable: score += 10
        if not log.role_based: score += 10
        
        log.verification_score = score
        if score == 100:
            log.final_status = "valid"
        elif score >= 80:
            log.final_status = "risky"
        else:
            log.final_status = "invalid"

        return self._save_log(log)
        
    def _save_log(self, log: EmailVerificationLog) -> EmailVerificationLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
