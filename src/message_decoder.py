"""Message Decoder - Extract text from NSAttributedString binary data"""

import logging
import plistlib
import struct
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MessageDecoder:
    """Handles decoding of NSAttributedString data from Messages app"""

    def __init__(self):
        self.decode_success_count = 0
        self.decode_failure_count = 0

    def decode_attributed_body(self, attributed_body: bytes) -> Optional[str]:
        """
        Decode NSAttributedString binary data to extract message text.

        Args:
            attributed_body: Binary data from attributedBody column

        Returns:
            Decoded text string or None if decoding fails
        """
        if not attributed_body:
            return None

        try:
            # Try multiple decoding strategies

            # Strategy 1: NSKeyedUnarchiver format (most common)
            text = self._decode_nskeyedarchiver(attributed_body)
            if text:
                self.decode_success_count += 1
                logger.debug(
                    f"Successfully decoded with NSKeyedUnarchiver: {text[:50]}..."
                )
                return text

            # Strategy 2: Binary plist format
            text = self._decode_binary_plist(attributed_body)
            if text:
                self.decode_success_count += 1
                logger.debug(f"Successfully decoded with binary plist: {text[:50]}...")
                return text

            # Strategy 3: Try to find embedded strings
            text = self._extract_embedded_strings(attributed_body)
            if text:
                self.decode_success_count += 1
                logger.debug(f"Successfully extracted embedded string: {text[:50]}...")
                return text

            # If all strategies fail
            self.decode_failure_count += 1
            logger.warning(
                f"Failed to decode attributedBody of length {len(attributed_body)}"
            )
            return None

        except Exception as e:
            self.decode_failure_count += 1
            logger.error(f"Error decoding attributedBody: {e}")
            return None

    def _decode_nskeyedarchiver(self, data: bytes) -> Optional[str]:
        """
        Decode NSKeyedUnarchiver format data.
        This is the primary format used by NSAttributedString.
        """
        try:
            # Check if this looks like NSKeyedArchiver data
            if not data.startswith(b"\x04\x0bstreamtyped"):
                return None

            # Look for NSString pattern - this indicates where the actual text is
            nsstring_marker = b"NSString"
            nsstring_idx = data.find(nsstring_marker)

            if nsstring_idx == -1:
                return None

            # Based on analysis, the pattern is:
            # NSString + 9 bytes + '+' + length_byte + actual_text
            # The text consistently appears 14 bytes after NSString

            text_offset = nsstring_idx + len(nsstring_marker) + 14

            # Make sure we have enough data
            if text_offset >= len(data):
                return None

            # Get the length byte (right before the text)
            length_byte_pos = text_offset - 1
            if length_byte_pos >= len(data):
                return None

            text_length = data[length_byte_pos]

            # Validate length is reasonable
            if text_length == 0 or text_length > 1000:
                return None

            # Extract the text
            text_end = text_offset + text_length
            if text_end > len(data):
                return None

            text_bytes = data[text_offset:text_end]

            try:
                decoded_text = text_bytes.decode("utf-8")
                if decoded_text.strip():
                    return decoded_text.strip()
            except UnicodeDecodeError:
                pass

            # If the fixed offset doesn't work, fall back to scanning
            return self._scan_for_text_after_nsstring(data, nsstring_idx)

        except Exception as e:
            logger.debug(f"NSKeyedArchiver decode failed: {e}")
            return None

    def _scan_for_text_after_nsstring(
        self, data: bytes, nsstring_idx: int
    ) -> Optional[str]:
        """Fallback method to scan for text after NSString marker"""
        try:
            search_start = nsstring_idx + 8  # Skip NSString

            # Look for the pattern: '+' followed by length byte and text
            plus_marker = b"+"
            plus_idx = data.find(plus_marker, search_start)

            if plus_idx == -1 or plus_idx + 2 >= len(data):
                return None

            # Length byte should be right after '+'
            length_byte = data[plus_idx + 1]

            if length_byte == 0 or length_byte > 1000:
                return None

            # Extract text
            text_start = plus_idx + 2
            text_end = text_start + length_byte

            if text_end > len(data):
                return None

            text_bytes = data[text_start:text_end]

            try:
                decoded_text = text_bytes.decode("utf-8")
                if decoded_text.strip() and decoded_text.isprintable():
                    return decoded_text.strip()
            except UnicodeDecodeError:
                pass

            return None

        except Exception as e:
            logger.debug(f"Text scanning failed: {e}")
            return None

    def _extract_string_from_archive_data(self, data: bytes) -> Optional[str]:
        """Extract string content from archive data"""
        try:
            # Look for length-prefixed strings
            i = 0
            while i < len(data) - 4:
                # Try reading as 4-byte length prefix
                if i + 4 < len(data):
                    try:
                        length = struct.unpack(">I", data[i : i + 4])[
                            0
                        ]  # Big-endian 4-byte int
                        if 0 < length < 10000 and i + 4 + length <= len(
                            data
                        ):  # Reasonable length
                            potential_string = data[i + 4 : i + 4 + length]
                            try:
                                text = potential_string.decode("utf-8")
                                if text.isprintable() and len(text.strip()) > 0:
                                    return text
                            except:
                                pass
                    except:
                        pass

                # Try reading as 2-byte length prefix
                if i + 2 < len(data):
                    try:
                        length = struct.unpack(">H", data[i : i + 2])[
                            0
                        ]  # Big-endian 2-byte int
                        if 0 < length < 1000 and i + 2 + length <= len(
                            data
                        ):  # Reasonable length
                            potential_string = data[i + 2 : i + 2 + length]
                            try:
                                text = potential_string.decode("utf-8")
                                if text.isprintable() and len(text.strip()) > 0:
                                    return text
                            except:
                                pass
                    except:
                        pass

                i += 1

            return None

        except Exception as e:
            logger.debug(f"String extraction failed: {e}")
            return None

    def _decode_binary_plist(self, data: bytes) -> Optional[str]:
        """Try to decode as binary plist format"""
        try:
            # Check for binary plist magic
            if data.startswith(b"bplist"):
                plist_data = plistlib.loads(data)

                # Look for string content in various possible locations
                text = self._extract_text_from_plist(plist_data)
                if text:
                    return text

            return None

        except Exception as e:
            logger.debug(f"Binary plist decode failed: {e}")
            return None

    def _extract_text_from_plist(self, plist_data: Any) -> Optional[str]:
        """Recursively extract text from plist data structure"""
        try:
            if isinstance(plist_data, str):
                return plist_data if plist_data.strip() else None

            elif isinstance(plist_data, dict):
                # Look for common NSAttributedString keys
                for key in ["NSString", "string", "text", "content"]:
                    if key in plist_data:
                        value = plist_data[key]
                        if isinstance(value, str) and value.strip():
                            return value

                # Recursively search all values
                for value in plist_data.values():
                    text = self._extract_text_from_plist(value)
                    if text:
                        return text

            elif isinstance(plist_data, list):
                # Search all list items
                for item in plist_data:
                    text = self._extract_text_from_plist(item)
                    if text:
                        return text

            return None

        except Exception as e:
            logger.debug(f"Plist text extraction failed: {e}")
            return None

    def _extract_embedded_strings(self, data: bytes) -> Optional[str]:
        """
        Last resort: try to find UTF-8 strings embedded in the binary data
        """
        try:
            # Look for contiguous UTF-8 text sequences
            potential_strings = []
            current_string = bytearray()

            for byte in data:
                # If byte is printable ASCII or common UTF-8
                if 32 <= byte <= 126 or byte in [
                    9,
                    10,
                    13,
                ]:  # Printable + tab, newline, CR
                    current_string.append(byte)
                elif 128 <= byte <= 255:  # Potential UTF-8 continuation
                    current_string.append(byte)
                else:
                    # End of potential string
                    if len(current_string) > 3:  # Minimum length
                        try:
                            text = current_string.decode("utf-8", errors="strict")
                            if text.strip() and len(text.strip()) > 3:
                                potential_strings.append(text.strip())
                        except:
                            pass
                    current_string = bytearray()

            # Check final string
            if len(current_string) > 3:
                try:
                    text = current_string.decode("utf-8", errors="strict")
                    if text.strip() and len(text.strip()) > 3:
                        potential_strings.append(text.strip())
                except:
                    pass

            # Return the longest meaningful string found
            if potential_strings:
                # Filter out common binary artifacts
                meaningful_strings = []
                for s in potential_strings:
                    # Skip strings that look like binary artifacts
                    if not any(
                        artifact in s.lower()
                        for artifact in [
                            "nsstring",
                            "nsattributed",
                            "nsmutable",
                            "nsarchive",
                            "streamtyped",
                            "nskeyedarchiver",
                        ]
                    ):
                        if len(s) > 3 and any(c.isalpha() for c in s):
                            meaningful_strings.append(s)

                if meaningful_strings:
                    # Return the longest string
                    return max(meaningful_strings, key=len)

            return None

        except Exception as e:
            logger.debug(f"Embedded string extraction failed: {e}")
            return None

    def get_decode_stats(self) -> Dict[str, int]:
        """Get decoding statistics"""
        total = self.decode_success_count + self.decode_failure_count
        success_rate = (self.decode_success_count / total * 100) if total > 0 else 0

        return {
            "success_count": self.decode_success_count,
            "failure_count": self.decode_failure_count,
            "total_attempts": total,
            "success_rate_percent": round(success_rate, 2),
        }

    def reset_stats(self):
        """Reset decoding statistics"""
        self.decode_success_count = 0
        self.decode_failure_count = 0


def extract_message_text(
    text: Optional[str], attributed_body: Optional[bytes]
) -> Optional[str]:
    """
    Convenience function to extract message text with fallback logic.

    Args:
        text: Text from the text column
        attributed_body: Binary data from attributedBody column

    Returns:
        Best available text content
    """
    # Primary: use text column if available
    if text and text.strip():
        return text.strip()

    # Fallback: decode attributedBody
    if attributed_body:
        decoder = MessageDecoder()
        decoded_text = decoder.decode_attributed_body(attributed_body)
        if decoded_text and decoded_text.strip():
            return decoded_text.strip()

    # No text available
    return None