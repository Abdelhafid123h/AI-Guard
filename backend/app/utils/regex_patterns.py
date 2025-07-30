import re

class NamedPattern:
    def __init__(self, name: str, pattern: str):
        self.name = name
        self.regex = re.compile(pattern)

class RegexPatterns:
    # TypeA - Données Personnelles Identifiantes
    NAME = NamedPattern("NAME", r'\b[A-Z][a-z]+(?:-[A-Z][a-z]+)?\s[A-Z][a-z]+\b')  # Gère les tirets
    FULL_NAME = NamedPattern("FULL_NAME", r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3}\b')  # 2-4 mots
    FIRSTNAME = NamedPattern("FIRSTNAME", r'\b(?:Jean|Pierre|Marie|Paul|Michel|Luc|Anne|Sophie|Claire|Thomas|Nicolas|Alexandre|François|David|Philippe|Laurent|Julien|Stéphane|Christophe|Patrick|Daniel|Mohamed|Ahmed|Fatima|Yasmine|Marie-Claire)\b')
    SOCIAL_SECURITY = NamedPattern("SSN", r'\b\d{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b')
    ID_CARD = NamedPattern("ID", r'\b[A-Z]{2}\d{6,8}\b')
    PASSPORT = NamedPattern("PASSPORT", r'\b\d{2}[A-Z]{2}\d{5}\b')
    DRIVING_LICENSE = NamedPattern("LICENSE", r'\b\d{9,12}\b')
    BIRTH_DATE = NamedPattern("BIRTH", r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}\b')
    BIRTH_PLACE = NamedPattern("BIRTH_PLACE", r'\bà\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
    
    # TypeB - Données Financières  
    CREDIT_CARD = NamedPattern("CC", r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')
    IBAN = NamedPattern("IBAN", r'\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{3}\b')
    BANK_ACCOUNT = NamedPattern("BANK", r'\b\d{5}[\s\-]?\d{5}[\s\-]?\d{11}[\s\-]?\d{2}\b')
    SECURITY_CODE = NamedPattern("CVV", r'\b\d{3,4}\b')
    PAYMENT_INFO = NamedPattern("PAYMENT", r'\b(Visa|MasterCard|Amex)\s[\*\d\s]{4,}\d{4}\b')
    
    # InfoPerso - Données de Contact et Localisation
    PHONE = NamedPattern("PHONE", r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
    EMAIL = NamedPattern("EMAIL", r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    ADDRESS = NamedPattern("ADDRESS", r'\d+\s[A-Za-z\s]+,\s?\d{5}\s[A-Za-z\s]+')
    POSTAL_CODE = NamedPattern("POSTAL", r'\b\d{5}\b')
    COMPANY = NamedPattern("COMPANY", r'\b[A-Z][a-zA-Z\s&]{2,}\s(SA|SARL|SAS|EURL|SNC)\b')
    IP_ADDRESS = NamedPattern("IP", r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

PII_PATTERNS = {
    # TypeA
    "name": RegexPatterns.NAME,
    "full_name": RegexPatterns.FULL_NAME,
    "firstname": RegexPatterns.FIRSTNAME,
    "social_security": RegexPatterns.SOCIAL_SECURITY,
    "id_card": RegexPatterns.ID_CARD,
    "passport": RegexPatterns.PASSPORT,
    "driving_license": RegexPatterns.DRIVING_LICENSE,
    "birth_date": RegexPatterns.BIRTH_DATE,
    "birth_place": RegexPatterns.BIRTH_PLACE,
    
    # TypeB
    "credit_card": RegexPatterns.CREDIT_CARD,
    "iban": RegexPatterns.IBAN,
    "bank_account": RegexPatterns.BANK_ACCOUNT,
    "security_code": RegexPatterns.SECURITY_CODE,
    "payment_info": RegexPatterns.PAYMENT_INFO,
    
    # InfoPerso
    "phone": RegexPatterns.PHONE,
    "email": RegexPatterns.EMAIL,
    "address": RegexPatterns.ADDRESS,
    "postal_code": RegexPatterns.POSTAL_CODE,
    "company": RegexPatterns.COMPANY,
    "ip_address": RegexPatterns.IP_ADDRESS
}