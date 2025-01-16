# X12 Parser

This Python library provides a robust and efficient parser for EDI X12 documents. It handles multiple character encodings, and provides convenient access to EDI data through a clean, object-oriented interface.

## Features

The parser supports all standard X12 envelope structures and provides comprehensive validation of control numbers, segment counts, and document structure. Key features include:

- Memory-efficient chunk-based processing for handling large files
- Support for multiple character encodings (ASCII, UTF-8, UTF-16, EBCDIC, etc.)
- Strict validation of control segments and envelope structure
- JSON serialization support for easy data integration
- Detailed error reporting for invalid X12 documents
- Clean, hierarchical access to parsed EDI data
