# Dune Archive System
# CMPE 321 Project 4
# 2021400282 2021400093

## Description
This is an implementation of the Dune Archive System, a simple database management system
that stores information about the planet Arrakis. The system supports creating types (tables),
creating records, deleting records, and searching for records by primary key.

## Requirements
- Python 3.x

## How to Run
The program takes an input file path as a command-line argument. To run the program, use:

```
python3 archive.py <input_file_path>
```

For example:
```
python3 archive.py input.txt
```

If no input file is specified, the program will default to 'input.txt' in the current directory.

## Input Format
The input file should contain operations, one per line, in the following formats:

1. Create a type (table):
   ```
   create type <type-name> <number-of-fields> <primary-key-order> <field1-name> <field1-type> <field2-name> <field2-type> ...
   ```
   Example: `create type house 6 1 name str origin str leader str military strength int wealth int spice production int`

2. Create a record:
   ```
   create record <type-name> <field1-value> <field2-value> ...
   ```
   Example: `create record house Atreides Caladan Duke 8000 5000 150`

3. Delete a record:
   ```
   delete record <type-name> <primary-key>
   ```
   Example: `delete record house Atreides`

4. Search for a record:
   ```
   search record <type-name> <primary-key>
   ```
   Example: `search record house Atreides`

## Output
The program produces two output files:

1. `output.txt`: Contains the results of search operations, with field values separated by spaces.

2. `log.csv`: A log file that records all operations with timestamps and their status (success or failure).

Additionally, a .txt file for each type will be created. Please do not delete those files after a run. The data will
be stored in those files. 

## File Structure
- `archive.py`: The main program file
- `catalog.txt`: Stores type definitions (created during execution)
- `<type-name>.txt`: Data files for each type (created during execution)
- `output.txt`: Output file for search results
- `log.csv`: Log file for operations

## Implementation Details
The system implements a simple file-based database with:
- Fixed-length records (25 characters per field)
- Slotted page organization with a bitmap to track occupied slots
- Maximum of 10 records per page
- Maximum of 100 pages per file
- Support for string and integer field types

## Error Handling
The system handles the following error cases:
- Creating a type with an existing name
- Creating a record with a primary key that already exists
- Deleting a record that doesn't exist
- Searching for a record that doesn't exist
- Operating on a type that doesn't exist

All errors are logged to the log file with a 'failure' status.
