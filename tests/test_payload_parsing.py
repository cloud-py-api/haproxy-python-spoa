import io
import ipaddress
import unittest

from haproxyspoa.spoa_data_types import parse_string, write_binary, write_string, write_typed_autodetect
from haproxyspoa.spoa_payloads import write_kv_list, parse_kv_list, parse_list_of_messages


class TestPayloadParsing(unittest.TestCase):

    def test_write_read_list_of_messages(self):
        buffer = io.BytesIO()

        message_name = "solar_system_communication"
        num_args = 4
        args = {
            "mercury": write_typed_autodetect(ipaddress.IPv4Address("192.168.1.23")),
            "venus": write_typed_autodetect(123456789),
            "earth": write_typed_autodetect("looks like a marble"),
            "mars": write_typed_autodetect(True),
        }

        buffer.write(write_string(message_name))
        buffer.write(bytes([num_args]))
        buffer.write(write_kv_list(args))

        self.assertEqual(
            buffer.getvalue(),
            b'\x1asolar_system_communication\x04\x07mercury\x06\xc0\xa8\x01\x17\x05venus\x04\xf5\xc2\xf8\xd5\x02'
            b'\x05earth\x08\x13looks like a marble\x04mars\x04\x01',
        )

        buffer.seek(0)
        messages = parse_list_of_messages(buffer)

        self.assertEqual(messages, {
            "solar_system_communication": {
                "mercury": ipaddress.IPv4Address("192.168.1.23"),
                "venus": 123456789,
                "earth": "looks like a marble",
                "mars": 1
            }
        })

    def test_string_with_bytes_above_0x7f(self):
        # A Cookie header whose value holds "%e4", which a proxy in front URL-decoded into the
        # single byte 0xE4 ("ä" in Latin-1), and a UTF-8 "ł" (0xC5 0x82). Raised
        # UnicodeDecodeError with ASCII, which killed the agent's connection.
        raw = b"cookie: a=b; session=iI6tu#w3\xe4CaJ; name=Pawe\xc5\x82"
        value = parse_string(io.BytesIO(write_binary(raw)))

        self.assertEqual(len(value), len(raw))
        self.assertEqual(write_string(value), write_binary(raw))

    def test_message_with_non_ascii_header_value(self):
        buffer = io.BytesIO()
        buffer.write(write_string("check-request"))
        buffer.write(bytes([1]))
        buffer.write(write_kv_list({"headers": b"\x08" + write_binary(b"referer: https://example.org/K\xe4se\r\n")}))

        buffer.seek(0)
        messages = parse_list_of_messages(buffer)

        self.assertEqual(
            messages["check-request"]["headers"].encode("latin-1"),
            b"referer: https://example.org/K\xe4se\r\n",
        )


if __name__ == '__main__':
    unittest.main()
