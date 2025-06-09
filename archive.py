# archive.py
import os
import time

CATALOG_FILE = "catalog.txt"
OUTPUT_FILE = "output.txt"
LOG_FILE = "log.csv"
MAX_RECORDS_PER_PAGE = 10
MAX_PAGES_PER_FILE = 100
FIELD_SIZE = 25  # Fixed size for all fields (int or str)

class TypeDefinition:
    def __init__(self, name, num_fields, primary_key_index, fields):
        self.name = name
        self.num_fields = num_fields
        self.primary_key_index = primary_key_index
        self.fields = fields  # List of (name, type, size)
        self.record_size = 1 + sum(FIELD_SIZE for _ in fields)

    def to_line(self):
        field_str = '|'.join([f"{fname}:{ftype}:{FIELD_SIZE}" for fname, ftype, _ in self.fields])
        return f"{self.name}|{self.num_fields}|{self.primary_key_index}|{field_str}"

    @staticmethod
    def from_line(line):
        parts = line.strip().split('|')
        name = parts[0]
        num_fields = int(parts[1])
        primary_key_index = int(parts[2])
        fields = []
        for field in parts[3:]:
            fname, ftype, fsize = field.split(':')
            fields.append((fname, ftype, int(fsize)))
        return TypeDefinition(name, num_fields, primary_key_index, fields)

class Catalog:
    def __init__(self):
        self.types = self.load_catalog()

    def load_catalog(self):
        types = {}
        if os.path.exists(CATALOG_FILE):
            with open(CATALOG_FILE, 'r') as f:
                for line in f:
                    td = TypeDefinition.from_line(line)
                    types[td.name] = td
        return types

    def save_type(self, td):
        with open(CATALOG_FILE, 'a') as f:
            f.write(td.to_line() + '\n')
        self.types[td.name] = td

    def has_type(self, name):
        return name in self.types

    def get_type(self, name):
        return self.types.get(name)

class Logger:
    def __init__(self):
        pass

    def log(self, command, status):
        timestamp = int(time.time())
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp}, {command}, {status}\n")

class OutputWriter:
    def __init__(self):
        open(OUTPUT_FILE, 'w').close()  # clear file

    def write(self, line):
        with open(OUTPUT_FILE, 'a') as f:
            f.write(line + '\n')

class Page:
    def __init__(self, page_number, record_size, max_records=MAX_RECORDS_PER_PAGE):
        self.page_number = page_number
        self.record_size = record_size
        self.max_records = max_records
        self.bitmap = [0] * max_records  # 0 = empty, 1 = occupied
        self.records = [None] * max_records
        self.num_records = 0

    def has_space(self):
        return self.num_records < self.max_records

    def add_record(self, record):
        for i in range(self.max_records):
            if self.bitmap[i] == 0:
                self.bitmap[i] = 1
                self.records[i] = record
                self.num_records += 1
                return i
        return -1

    def get_record(self, slot_index):
        if 0 <= slot_index < self.max_records and self.bitmap[slot_index] == 1:
            return self.records[slot_index]
        return None

    def delete_record(self, slot_index):
        if 0 <= slot_index < self.max_records and self.bitmap[slot_index] == 1:
            self.bitmap[slot_index] = 0
            self.records[slot_index] = None
            self.num_records -= 1
            return True
        return False

    def serialize(self):
        header = f"{self.page_number}|{self.num_records}|{''.join(map(str, self.bitmap))}|"
        content = ''
        for record in self.records:
            if record:
                content += record
            else:
                content += '0' * self.record_size  # Empty record placeholder
        return header + content

    @staticmethod
    def deserialize(page_str, record_size):
        parts = page_str.split('|', 3)
        page_number = int(parts[0])
        num_records = int(parts[1])
        bitmap = [int(b) for b in parts[2]]
        page = Page(page_number, record_size)
        page.bitmap = bitmap
        page.num_records = num_records
        content = parts[3]
        for i in range(len(bitmap)):
            if bitmap[i] == 1:
                start = i * record_size
                page.records[i] = content[start:start+record_size]
        return page

class RecordManager:
    def __init__(self, td: TypeDefinition):
        self.td = td
        self.file_path = f"{td.name}.txt"

    def format_record(self, values):
        record = '1'  # Validity flag
        for (value, (_, ftype, _)) in zip(values, self.td.fields):
            if ftype == 'int':
                if not value.lstrip('-').isdigit():
                    raise ValueError(f"Invalid integer value: {value}")
                value = str(int(value))
            record += value.ljust(FIELD_SIZE)
        return record

    def parse_record(self, record_str):
        if not record_str or record_str[0] != '1':
            return None
        offset = 1
        values = []
        for _, ftype, _ in self.td.fields:
            field = record_str[offset:offset+FIELD_SIZE].strip()
            values.append(field)
            offset += FIELD_SIZE
        return values

    def get_primary_key(self, values):
        return values[self.td.primary_key_index]

    def read_page(self, file, page_number):
        file.seek(0)
        while True:
            line = file.readline().strip()
            if not line:
                return None
            if int(line.split('|')[0]) == page_number:
                return line

    def write_page(self, page):
        pages = []
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        pages.append(line.strip())
        for i, p in enumerate(pages):
            if int(p.split('|')[0]) == page.page_number:
                pages[i] = page.serialize()
                break
        else:
            pages.append(page.serialize())
        with open(self.file_path, 'w') as f:
            for p in pages:
                f.write(p + '\n')

    def record_exists(self, pk):
        if not os.path.exists(self.file_path):
            return False
        with open(self.file_path, 'r') as f:
            page_number = 0
            while True:
                page_str = self.read_page(f, page_number)
                if not page_str:
                    break
                page = Page.deserialize(page_str, self.td.record_size)
                for i in range(page.max_records):
                    if page.bitmap[i] == 1:
                        record = page.records[i]
                        parsed = self.parse_record(record)
                        if parsed and self.get_primary_key(parsed) == pk:
                            return True
                page_number += 1
        return False

    def create_record(self, values):
        pk = self.get_primary_key(values)
        if self.record_exists(pk):
            return False
        record = self.format_record(values)
        page_found = False
        page_number = 0
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                while page_number < MAX_PAGES_PER_FILE:
                    page_str = self.read_page(f, page_number)
                    if not page_str:
                        break
                    page = Page.deserialize(page_str, self.td.record_size)
                    if page.has_space():
                        page.add_record(record)
                        self.write_page(page)
                        return True
                    page_number += 1
        page = Page(page_number, self.td.record_size)
        page.add_record(record)
        with open(self.file_path, 'a' if os.path.exists(self.file_path) else 'w') as f:
            f.write(page.serialize() + '\n')
        return True

    def delete_record(self, pk):
        if not os.path.exists(self.file_path):
            return False
        with open(self.file_path, 'r') as f:
            page_number = 0
            while True:
                page_str = self.read_page(f, page_number)
                if not page_str:
                    break
                page = Page.deserialize(page_str, self.td.record_size)
                for i in range(page.max_records):
                    if page.bitmap[i] == 1:
                        record = page.records[i]
                        parsed = self.parse_record(record)
                        if parsed and self.get_primary_key(parsed) == pk:
                            page.delete_record(i)
                            self.write_page(page)
                            return True
                page_number += 1
        return False

    def search_record(self, pk):
        if not os.path.exists(self.file_path):
            return None
        with open(self.file_path, 'r') as f:
            page_number = 0
            while True:
                page_str = self.read_page(f, page_number)
                if not page_str:
                    break
                page = Page.deserialize(page_str, self.td.record_size)
                for i in range(page.max_records):
                    if page.bitmap[i] == 1:
                        record = page.records[i]
                        parsed = self.parse_record(record)
                        if parsed and self.get_primary_key(parsed) == pk:
                            return parsed
                page_number += 1
        return None

if __name__ == '__main__':
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'input.txt'
    catalog = Catalog()
    logger = Logger()
    output = OutputWriter()
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            command = parts[0]
            try:
                if command == 'create' and parts[1] == 'type':
                    type_name = parts[2]
                    num_fields = int(parts[3])
                    pk_index = int(parts[4]) - 1
                    fields = []
                    for i in range(num_fields):
                        fname = parts[5 + i * 2]
                        ftype = parts[6 + i * 2]
                        fields.append((fname, ftype, FIELD_SIZE))
                    if catalog.has_type(type_name):
                        logger.log(line, 'failure')
                    else:
                        td = TypeDefinition(type_name, num_fields, pk_index, fields)
                        catalog.save_type(td)
                        logger.log(line, 'success')
                elif command == 'create' and parts[1] == 'record':
                    type_name = parts[2]
                    values = parts[3:]
                    if not catalog.has_type(type_name):
                        logger.log(line, 'failure')
                        continue
                    td = catalog.get_type(type_name)
                    rm = RecordManager(td)
                    if rm.create_record(values):
                        logger.log(line, 'success')
                    else:
                        logger.log(line, 'failure')
                elif command == 'delete' and parts[1] == 'record':
                    type_name = parts[2]
                    pk = parts[3]
                    if not catalog.has_type(type_name):
                        logger.log(line, 'failure')
                        continue
                    td = catalog.get_type(type_name)
                    rm = RecordManager(td)
                    if rm.delete_record(pk):
                        logger.log(line, 'success')
                    else:
                        logger.log(line, 'failure')
                elif command == 'search' and parts[1] == 'record':
                    type_name = parts[2]
                    pk = parts[3]
                    if not catalog.has_type(type_name):
                        logger.log(line, 'failure')
                        continue
                    td = catalog.get_type(type_name)
                    rm = RecordManager(td)
                    result = rm.search_record(pk)
                    if result:
                        output.write(' '.join(result))
                        logger.log(line, 'success')
                    else:
                        logger.log(line, 'failure')
                else:
                    logger.log(line, 'failure')
            except Exception:
                logger.log(line, 'failure')
