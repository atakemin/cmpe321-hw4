# archive.py
import os
import time

CATALOG_FILE = "catalog.txt"
OUTPUT_FILE = "output.txt"
LOG_FILE = "log.csv"
MAX_RECORDS_PER_PAGE = 10
MAX_PAGES_PER_FILE = 100

class TypeDefinition:
    def __init__(self, name, num_fields, primary_key_index, fields):
        self.name = name
        self.num_fields = num_fields
        self.primary_key_index = primary_key_index
        self.fields = fields  # List of (name, type, size)
        self.record_size = 1 + sum(size for _, _, size in fields)  # 1 byte for validity

    def to_line(self):
        field_str = '|'.join([f"{fname}:{ftype}:{fsize}" for fname, ftype, fsize in self.fields])
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

class RecordManager:
    def __init__(self, td: TypeDefinition):
        self.td = td
        self.file_path = f"{td.name}.txt"

    def format_record(self, values):
        record = '1'  # Validity flag as char
        for (value, (_, ftype, fsize)) in zip(values, self.td.fields):
            if ftype == 'int':
                value = str(int(value))
            record += value.ljust(fsize)
        return record

    def parse_record(self, record_str):
        if not record_str or record_str[0] != '1':
            return None
        offset = 1
        values = []
        for _, ftype, fsize in self.td.fields:
            field = record_str[offset:offset+fsize].strip()
            if ftype == 'int':
                values.append(str(int(field)))
            else:
                values.append(field)
            offset += fsize
        return values

    def get_primary_key(self, values):
        return values[self.td.primary_key_index]

    def record_exists(self, pk):
        if not os.path.exists(self.file_path):
            return False
        with open(self.file_path, 'r') as f:
            for line in f:
                if line.startswith('1'):
                    if self.get_primary_key(self.parse_record(line.strip())) == pk:
                        return True
        return False

    def create_record(self, values):
        pk = self.get_primary_key(values)
        if self.record_exists(pk):
            return False
        record = self.format_record(values)
        with open(self.file_path, 'a') as f:
            f.write(record + '\n')
        return True

    def delete_record(self, pk):
        if not os.path.exists(self.file_path):
            return False
        updated = False
        lines = []
        with open(self.file_path, 'r') as f:
            for line in f:
                if line.startswith('1') and self.get_primary_key(self.parse_record(line.strip())) == pk:
                    lines.append('0' + line[1:])
                    updated = True
                else:
                    lines.append(line.rstrip())
        if updated:
            with open(self.file_path, 'w') as f:
                for l in lines:
                    f.write(l + '\n')
        return updated

    def search_record(self, pk):
        if not os.path.exists(self.file_path):
            return None
        with open(self.file_path, 'r') as f:
            for line in f:
                if line.startswith('1'):
                    parsed = self.parse_record(line.strip())
                    if self.get_primary_key(parsed) == pk:
                        return parsed
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
                        fsize = 4 if ftype == 'int' else 12  # default str size
                        fields.append((fname, ftype, fsize))
                    if catalog.has_type(type_name):
                        logger.log(line, 'failure')
                    else:
                        td = TypeDefinition(type_name, num_fields, pk_index, fields)
                        catalog.save_type(td)
                        open(f"{type_name}.txt", 'w').close()
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
            except Exception as e:
                logger.log(line, 'failure')
