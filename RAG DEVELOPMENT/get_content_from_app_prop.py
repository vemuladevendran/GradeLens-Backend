from configparser import ConfigParser

def read_properties(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Add dummy section to make it compatible
    lines.insert(0, '[dummy_section]\n')

    parser = ConfigParser()
    parser.read_string(''.join(lines))
    return parser['dummy_section']