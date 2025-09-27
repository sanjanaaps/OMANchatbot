# -*- coding: utf-8 -*-
"""
Sensitive Data Masking Module
Masks sensitive information like account numbers, SSNs, etc. based on user department
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SensitiveDataMasker:
    """Class to handle masking of sensitive information based on user permissions"""
    
    def __init__(self):
        # Define sensitive data patterns - only account numbers and phone numbers
        self.patterns = {
            'account_number': [
                r'\b(?:account|acct)[\s#:]*\d{10,20}\b',  # Account numbers with context
                r'\b[A-Z]{2}\d{10,15}\b',  # Bank codes + account numbers
            ],
            'phone_number': [
                r'\b(?:phone|tel|mobile|cell)[\s#:]*[\(\)\d\s\-\+\.]{10,20}\b',  # Phone numbers with context
            ]
        }
        
        # Define masking characters
        self.mask_char = '*'
        
        # Define departments that should have sensitive data masked
        self.masked_departments = ['Policy', 'Legal', 'Compliance', 'Audit']
        
        # Define departments that can see sensitive data
        self.unmasked_departments = ['Finance', 'Operations', 'IT', 'Currency', 'Banking']
    
    def should_mask_data(self, user_department: str) -> bool:
        """
        Determine if sensitive data should be masked based on user department
        
        Args:
            user_department: The department of the logged-in user
            
        Returns:
            bool: True if data should be masked, False otherwise
        """
        if not user_department:
            return True  # Default to masking if no department specified
            
        department = user_department.lower()
        
        # Check if department is in masked list
        if any(masked_dept.lower() in department for masked_dept in self.masked_departments):
            return True
            
        # Check if department is in unmasked list
        if any(unmasked_dept.lower() in department for unmasked_dept in self.unmasked_departments):
            return False
            
        # Default to masking for unknown departments
        return True
    
    def mask_text(self, text: str, user_department: str, mask_types: Optional[List[str]] = None) -> str:
        """
        Mask sensitive information in text based on user department
        
        Args:
            text: The text to mask
            user_department: The department of the logged-in user
            mask_types: Specific types of data to mask (if None, masks all)
            
        Returns:
            str: Text with sensitive information masked
        """
        if not self.should_mask_data(user_department):
            return text
            
        if not text or not text.strip():
            return text
            
        masked_text = text
        
        # If no specific types specified, mask all types
        if mask_types is None:
            mask_types = list(self.patterns.keys())
        
        # Apply masking for each specified type
        for data_type in mask_types:
            if data_type in self.patterns:
                for pattern in self.patterns[data_type]:
                    masked_text = self._apply_pattern_mask(masked_text, pattern, data_type)
        
        return masked_text
    
    def _apply_pattern_mask(self, text: str, pattern: str, data_type: str) -> str:
        """
        Apply masking to a specific pattern
        
        Args:
            text: The text to mask
            pattern: The regex pattern to match
            data_type: The type of data being masked
            
        Returns:
            str: Text with the pattern masked
        """
        # Use the new precise masking functions for specific data types only
        if data_type == 'account_number':
            return self._mask_account_numbers_precise(text)
        elif data_type == 'phone_number':
            return self._mask_phone_numbers_precise(text)
        
        # For other data types, return text unchanged (no masking)
        return text
    
    def _mask_account_numbers_precise(self, text: str) -> str:
        """
        Use the precise account number masking function
        """
        return detect_and_mask_account_numbers(text, self.mask_char)
    
    def _mask_phone_numbers_precise(self, text: str) -> str:
        """
        Use the precise phone number masking function
        """
        return detect_and_mask_phone_numbers(text, self.mask_char)
    
    def get_masking_info(self, user_department: str) -> Dict[str, any]:
        """
        Get information about what data will be masked for a user
        
        Args:
            user_department: The department of the logged-in user
            
        Returns:
            dict: Information about masking settings
        """
        will_mask = self.should_mask_data(user_department)
        
        return {
            'will_mask': will_mask,
            'department': user_department,
            'masked_departments': self.masked_departments,
            'unmasked_departments': self.unmasked_departments,
            'masked_data_types': list(self.patterns.keys()) if will_mask else [],
            'mask_character': self.mask_char
        }

# Simple masking functions for account numbers and phone numbers
def detect_and_mask_account_numbers(text, mask_char='*'):
    """
    Simple account number masking
    """
    # Pattern to match "Account: 1234567890123456" format
    pattern = r'(Account:\s*)(\d{10,20})'
    
    def mask_match(match):
        prefix = match.group(1)
        number = match.group(2)
        if len(number) > 4:
            masked_number = mask_char * (len(number) - 4) + number[-4:]
            return prefix + masked_number
        return match.group(0)
    
    return re.sub(pattern, mask_match, text, flags=re.IGNORECASE)

def detect_and_mask_phone_numbers(text, mask_char='*'):
    """
    Simple phone number masking
    """
    # Pattern to match "Phone: (555) 123-4567" format
    pattern = r'(Phone:\s*)([\(\)\d\s\-\+\.]{10,20})'
    
    def mask_match(match):
        prefix = match.group(1)
        phone = match.group(2)
        # Extract digits only
        digits = re.sub(r'[^\d]', '', phone)
        if len(digits) >= 7:
            # Keep first 3 and last 4 digits
            if len(phone) >= 7:
                masked_phone = phone[:3] + mask_char * (len(phone) - 7) + phone[-4:]
                return prefix + masked_phone
        return match.group(0)
    
    return re.sub(pattern, mask_match, text, flags=re.IGNORECASE)

# Global instance
sensitive_data_masker = SensitiveDataMasker()

def mask_sensitive_data(text: str, user_department: str, mask_types: Optional[List[str]] = None) -> str:
    """
    Convenience function to mask sensitive data
    
    Args:
        text: The text to mask
        user_department: The department of the logged-in user
        mask_types: Specific types of data to mask (if None, masks all)
        
    Returns:
        str: Text with sensitive information masked
    """
    return sensitive_data_masker.mask_text(text, user_department, mask_types)

def should_mask_for_user(user_department: str) -> bool:
    """
    Convenience function to check if data should be masked for a user
    
    Args:
        user_department: The department of the logged-in user
        
    Returns:
        bool: True if data should be masked, False otherwise
    """
    return sensitive_data_masker.should_mask_data(user_department)

def get_masking_info(user_department: str) -> Dict[str, any]:
    """
    Convenience function to get masking information for a user
    
    Args:
        user_department: The department of the logged-in user
        
    Returns:
        dict: Information about masking settings
    """
    return sensitive_data_masker.get_masking_info(user_department)
