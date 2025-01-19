import codecs
from dataclasses import dataclass
import io
from typing import List, Dict, Optional, Any, Tuple


class X12ParsingError(Exception):
    """Custom exception for X12 parsing errors"""
    pass


@dataclass
class X12Element:
    """Represents a single X12 element within a segment"""
    value: str
    position: int

    def __post_init__(self):
        if self.value and self.value.strip() == '':
            self.value = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'value': self.value,
            'position': self.position
        }


@dataclass
class X12Segment:
    """Represents an X12 segment containing elements"""
    segment_id: str
    elements: List[X12Element]
    position: int

    def get_element(self, position: int) -> Optional[str]:
        """Get element value by position"""
        for element in self.elements:
            if element.position == position:
                return element.value
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'elements': [element.to_dict() for element in self.elements],
            'position': self.position
        }


@dataclass
class X12TransactionSet:
    """Represents an X12 transaction set (ST-SE)"""
    control_number: str
    doc_type: str
    segments: List[X12Segment]
    segment_count: int = 0
    
    def validate(self) -> None:
        """Validate transaction set structure"""
        if not self.segments:
            raise X12ParsingError('Transaction set has no segments')
            
        if self.segments[0].segment_id != 'ST':
            raise X12ParsingError('Transaction set must start with ST segment')
            
        if self.segments[-1].segment_id != 'SE':
            raise X12ParsingError('Transaction set must end with SE segment')
            
        actual_count = len(self.segments)
        se_count = int(self.segments[-1].get_element(1))
        if se_count != actual_count:
            raise X12ParsingError(f'SE segment count ({se_count}) does not match actual segment count ({actual_count})')

    def _get_segment_by_position(self, segment_id: str, position: int) -> Optional[X12Segment]:
        """Get segment matching both ID and position"""
        for segment in self.segments:
            if segment.segment_id == segment_id and segment.position == position:
                return segment
        return None

    def _get_segment_by_occurrence(self, segment_id: str, occurrence: int) -> Optional[X12Segment]:
        """Get the nth occurrence of a segment with given ID"""
        if occurrence < 1:
            return None

        count = 0
        for segment in self.segments:
            if segment.segment_id == segment_id:
                count += 1
                if count == occurrence:
                    return segment
        return None

    def _get_first_segment(self, segment_id: str) -> Optional[X12Segment]:
        """Get first segment matching the ID"""
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        return None

    def get_segment(self, segment_id: str, position: Optional[int] = None, 
                   occurrence: Optional[int] = None) -> Optional[X12Segment]:
        """Get segment by ID with optional position or occurrence specification"""
        if position is not None:
            return self._get_segment_by_position(segment_id, position)
            
        if occurrence is not None:
            return self._get_segment_by_occurrence(segment_id, occurrence)
            
        return self._get_first_segment(segment_id)
    
    def get_segments(self, segment_id: str) -> List[X12Segment]:
        """Get all segments with ID"""
        return [segment for segment in self.segments if segment.segment_id == segment_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'control_number': self.control_number,
            'doc_type': self.doc_type,
            'segments': [segment.to_dict() for segment in self.segments],
            'segment_count': self.segment_count
        }


@dataclass
class X12FunctionalGroup:
    """Represents an X12 functional group (GS-GE)"""
    control_number: str
    sender_id: str
    receiver_id: str
    date: str
    time: str
    version: str
    transaction_sets: List[X12TransactionSet]
    gs_segment: Optional[X12Segment] = None
    ge_segment: Optional[X12Segment] = None
    
    def validate(self) -> None:
        """Validate functional group structure"""
        if not self.transaction_sets:
            raise X12ParsingError('Functional group has no transaction sets')
            
        if not self.gs_segment:
            raise X12ParsingError('Functional group missing GS segment')
            
        if self.ge_segment:
            declared_count = int(self.ge_segment.get_element(1))
            if len(self.transaction_sets) != declared_count:
                raise X12ParsingError(f'Transaction set count mismatch: declared {declared_count}, actual {len(self.transaction_sets)}')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'control_number': self.control_number,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'date': self.date,
            'time': self.time,
            'version': self.version,
            'gs_segment': self.gs_segment.to_dict() if self.gs_segment else None,
            'ge_segment': self.ge_segment.to_dict() if self.ge_segment else None,
            'transaction_sets': [ts.to_dict() for ts in self.transaction_sets]
        }


@dataclass
class X12Interchange:
    """Represents an X12 interchange (ISA-IEA)"""
    control_number: str
    sender_id: str
    receiver_id: str
    date: str
    time: str
    version: str
    element_separator: str
    segment_terminator: str
    component_separator: str
    functional_groups: List[X12FunctionalGroup]
    isa_segment: Optional[X12Segment] = None
    iea_segment: Optional[X12Segment] = None
    
    def validate(self) -> None:
        """Validate interchange structure"""
        if not self.functional_groups:
            raise X12ParsingError('Interchange has no functional groups')
            
        if not self.isa_segment:
            raise X12ParsingError('Interchange missing ISA segment')
            
        if self.iea_segment:
            declared_count = int(self.iea_segment.get_element(1))
            if len(self.functional_groups) != declared_count:
                raise X12ParsingError(f'Functional group count mismatch: declared {declared_count}, actual {len(self.functional_groups)}')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'control_number': self.control_number,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'date': self.date,
            'time': self.time,
            'version': self.version,
            'element_separator': self.element_separator,
            'segment_terminator': self.segment_terminator,
            'component_separator': self.component_separator,
            'isa_segment': self.isa_segment.to_dict() if self.isa_segment else None,
            'iea_segment': self.iea_segment.to_dict() if self.iea_segment else None,
            'functional_groups': [fg.to_dict() for fg in self.functional_groups]
        }


class X12Parser:
    """Main parser class for X12 documents"""
    ISA_SEGMENT_LENGTH = 106
    
    def __init__(self, chunk_size: int = 8192, encoding: str = 'ascii'):
        """Initialize X12 parser with specified chunk size and encoding"""
        if chunk_size < 0:
            raise ValueError(f'Chunk size must be at least {self.MINIMUM_CHUNK_SIZE} bytes')
            
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.reset()

    def reset(self) -> None:
        """Reset parser state for new file processing"""
        self.text_buffer = ''
        self.current_interchange = None
        self.current_functional_group = None
        self.current_transaction_set = None
        self.interchanges = []

    def _detect_encoding(self, binary_file) -> Tuple[str, int]:
        """Detect file encoding based on BOM"""
        # Read initial bytes to check for BOM
        start_bytes = binary_file.read(4)
        binary_file.seek(0)
        
        # Check for known BOMs
        if start_bytes.startswith(codecs.BOM_UTF8):
            return 'utf-8-sig', 3
        elif start_bytes.startswith(codecs.BOM_UTF16_LE):
            return 'utf-16le', 2
        elif start_bytes.startswith(codecs.BOM_UTF16_BE):
            return 'utf-16be', 2
        elif start_bytes.startswith(codecs.BOM_UTF16):
            return 'utf-16', 2
        elif start_bytes.startswith(codecs.BOM_UTF32_LE):
            return 'utf-32le', 4
        elif start_bytes.startswith(codecs.BOM_UTF32_BE):
            return 'utf-32be', 4
        elif start_bytes.startswith(codecs.BOM_UTF32):
            return 'utf-32', 4
        
        return self.encoding, 0

    def _read_isa_segment(self, text_stream: io.TextIOBase) -> Tuple[str, str, str]:
        """Read and validate ISA segment, return separators"""
        while len(self.text_buffer) < self.ISA_SEGMENT_LENGTH:
            next_chunk = text_stream.read(self.chunk_size)
            if not next_chunk:
                raise X12ParsingError('Incomplete ISA segment at start of file')
            self.text_buffer += next_chunk

        if not self.text_buffer.startswith('ISA'):
            raise X12ParsingError("File must start with ISA segment")
        
        element_separator = self.text_buffer[3]
        component_separator = self.text_buffer[104]
        segment_terminator = self.text_buffer[105]
        
        if not all([element_separator, component_separator, segment_terminator]):
            raise X12ParsingError('Could not determine separators from ISA segment')
            
        return element_separator, component_separator, segment_terminator

    def _create_segment(self, segment_id: str, elements: List[str], position: int) -> X12Segment:
        """Create a segment object from parsed elements"""
        return X12Segment(
            segment_id=segment_id,
            elements=[X12Element(value=value.strip() if value.strip() else '', position=i) 
                     for i, value in enumerate(elements[1:], start=1)],
            position=position
        )

    def parse_file(self, file_path: str) -> List[X12Interchange]:
        """Parse an X12 file and return list of interchanges"""
        self.reset()
        
        with open(file_path, 'rb') as binary_file:
            # Detect encoding from BOM or fall back to specified encoding
            detected_encoding, skip_bytes = self._detect_encoding(binary_file)
            binary_file.seek(skip_bytes)
            text_stream = io.TextIOWrapper(binary_file, encoding=detected_encoding)
            element_separator, component_separator, segment_terminator = self._read_isa_segment(text_stream)
            
            while True:
                self._process_chunk(element_separator, component_separator, segment_terminator)
                
                if not self.text_buffer or self.text_buffer[-1] != segment_terminator:
                    chunk = text_stream.read(self.chunk_size)
                    if not chunk:
                        if self.text_buffer.strip():
                            raise X12ParsingError(f'Incomplete segment at end of file: {self.text_buffer.strip()}')
                        break
                    self.text_buffer += chunk
            
            self._validate_final_state()
                
        return self.interchanges

    def _validate_final_state(self) -> None:
        """Validate parser state at end of file"""
        if self.current_transaction_set:
            raise X12ParsingError('Unclosed transaction set at end of file')
        if self.current_functional_group:
            raise X12ParsingError('Unclosed functional group at end of file')
        if self.current_interchange:
            raise X12ParsingError('Unclosed interchange at end of file')

    def _process_chunk(self, element_separator: str, component_separator: str, segment_terminator: str) -> None:
        """Process a chunk of X12 data"""
        while self.text_buffer:
            terminator_pos = self.text_buffer.find(segment_terminator)
            if terminator_pos == -1:
                break
                
            segment_str = self.text_buffer[:terminator_pos].strip()
            self.text_buffer = self.text_buffer[terminator_pos + len(segment_terminator):]
                
            if not segment_str:  # Empty segment
                continue
            
            elements = segment_str.split(element_separator)
            segment_id = elements[0]
            try:
                self._process_segment(segment_id, elements, element_separator, 
                                      component_separator, segment_terminator)
            except Exception as e:
                raise X12ParsingError(f'Error processing segment "{segment_str}": {str(e)}')

    def _process_segment(self, segment_id: str, elements: List[str], element_separator: str,
                         component_separator: str, segment_terminator: str) -> None:
        """Process a segment based on its type"""
        if segment_id == 'ISA':
            self._process_isa_segment(elements, element_separator, component_separator, segment_terminator)
        elif segment_id == 'IEA':
            self._process_iea_segment(elements)
        elif segment_id == 'GS':
            self._process_gs_segment(elements)
        elif segment_id == 'GE':
            self._process_ge_segment(elements)
        elif segment_id == 'ST':
            self._process_st_segment(elements)
        elif segment_id == 'SE':
            self._process_se_segment(elements)
        elif self.current_transaction_set:
            self._process_data_segment(segment_id, elements)
        else:
            raise X12ParsingError(f'Segment {segment_id} found outside of expected context')

    def _format_entity_id(self, qualifier: str, entity_id: str) -> str:
        """Format entity ID with qualifier"""
        return f'{qualifier}:{entity_id}' if qualifier.strip() else entity_id.strip()

    def _process_isa_segment(self, elements: List[str], element_separator: str,
                             component_separator: str, segment_terminator: str) -> None:
        """Process ISA segment and create new interchange"""
        if len(elements) != 17:
            raise X12ParsingError('ISA segment must have 16 elements')
            
        if self.current_interchange:
            raise X12ParsingError('Found ISA segment while previous interchange is still open')
            
        formatted_sender = self._format_entity_id(elements[5].strip(), elements[6].strip())
        formatted_receiver = self._format_entity_id(elements[7].strip(), elements[8].strip())
            
        isa_segment = self._create_segment('ISA', elements, 1)
            
        self.current_interchange = X12Interchange(
            control_number=elements[13],
            sender_id=formatted_sender,
            receiver_id=formatted_receiver,
            date=elements[9],
            time=elements[10],
            version=elements[12],
            element_separator=element_separator,
            component_separator=component_separator,
            segment_terminator=segment_terminator,
            functional_groups=[],
            isa_segment=isa_segment
        )

    def _process_iea_segment(self, elements: List[str]) -> None:
        """Process IEA segment and finalize interchange"""
        if len(elements) != 3:
            raise X12ParsingError('IEA segment must have 2 elements')
            
        if not self.current_interchange:
            raise X12ParsingError('IEA segment found without matching ISA')
            
        iea_segment = self._create_segment('IEA', elements, 2)
        self.current_interchange.iea_segment = iea_segment
            
        if elements[2] != self.current_interchange.control_number:
            raise X12ParsingError('IEA control number does not match ISA')
            
        self.current_interchange.validate()
        self.interchanges.append(self.current_interchange)
        self.current_interchange = None

    def _process_gs_segment(self, elements: List[str]) -> None:
        """Process GS segment and create new functional group"""
        if len(elements) != 9:
            raise X12ParsingError('GS segment must have 8 elements')
            
        if not self.current_interchange:
            raise X12ParsingError('GS segment found outside of interchange')
            
        gs_segment = self._create_segment('GS', elements, 1)
            
        self.current_functional_group = X12FunctionalGroup(
            control_number=elements[6],
            sender_id=elements[2],
            receiver_id=elements[3],
            date=elements[4],
            time=elements[5],
            version=elements[8],
            transaction_sets=[],
            gs_segment=gs_segment
        )
        self.current_interchange.functional_groups.append(self.current_functional_group)

    def _process_ge_segment(self, elements: List[str]) -> None:
        """Process GE segment and finalize functional group"""
        if len(elements) != 3:
            raise X12ParsingError('GE segment must have 2 elements')
            
        if not self.current_functional_group:
            raise X12ParsingError('GE segment found without matching GS')
            
        ge_segment = self._create_segment('GE', elements, 2)
        self.current_functional_group.ge_segment = ge_segment
            
        self._validate_ge_segment(elements)
        self.current_functional_group.validate()
        self.current_functional_group = None
        
    def _validate_ge_segment(self, elements: List[str]) -> None:
        """Validate GE segment control numbers and counts"""
        actual_count = len(self.current_functional_group.transaction_sets)
        declared_count = int(elements[1])
        if actual_count != declared_count:
            raise X12ParsingError(f'GE transaction set count ({declared_count}) does not match actual count ({actual_count})')
            
        if elements[2] != self.current_functional_group.control_number:
            raise X12ParsingError('GE control number does not match GS')

    def _process_st_segment(self, elements: List[str]) -> None:
        """Process ST segment and create new transaction set"""
        if len(elements) != 3:
            raise X12ParsingError('ST segment must have 2 elements')
            
        if not self.current_functional_group:
            raise X12ParsingError('ST segment found outside of functional group')
            
        st_segment = self._create_segment('ST', elements, 1)
        
        self.current_transaction_set = X12TransactionSet(
            control_number=elements[2],
            doc_type=elements[1],
            segments=[st_segment],
            segment_count=1
        )

    def _process_se_segment(self, elements: List[str]) -> None:
        """Process SE segment and finalize transaction set"""
        if len(elements) != 3:
            raise X12ParsingError('SE segment must have 2 elements')
            
        if not self.current_transaction_set:
            raise X12ParsingError('SE segment found without matching ST')
        
        self.current_transaction_set.segment_count += 1
        se_segment = self._create_segment('SE', elements, self.current_transaction_set.segment_count)
        self.current_transaction_set.segments.append(se_segment)
        
        if elements[2] != self.current_transaction_set.control_number:
            raise X12ParsingError('SE control number does not match ST')
            
        self.current_transaction_set.validate()
        
        if self.current_functional_group:
            self.current_functional_group.transaction_sets.append(self.current_transaction_set)
        
        self.current_transaction_set = None

    def _process_data_segment(self, segment_id: str, elements: List[str]) -> None:
        """Process a data segment within a transaction set"""
        if not self.current_transaction_set:
            raise X12ParsingError(f'Data segment {segment_id} found outside of transaction set')
        
        self.current_transaction_set.segment_count += 1
        segment = self._create_segment(segment_id, elements, self.current_transaction_set.segment_count)
        self.current_transaction_set.segments.append(segment)
