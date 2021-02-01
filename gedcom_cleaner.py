from typing import List

FORM_KEYS_ = {
    'CTRY': 'Country',
    'CITY': 'City',
    'STAE': 'State',
    'POST': 'Postal Code',
}


def process_event(event_lines: List[str]) -> List[str]:
    if not event_lines:
        return event_lines
    event_type = event_lines[0].strip().lstrip('1').strip()
    if event_type not in ['BIRT', 'DEAT', 'BURI', 'RESI']:
        return event_lines
    address_keys = []
    address_vals = []
    place = None
    event_lines_to_keep = []
    for i, line in enumerate(event_lines):
        key, value = line[2:6].strip(), line[7:].strip()
        if key == 'PLAC':
            place = value
        elif key == 'ADDR' or key == 'CONT':
            pass
        elif key in FORM_KEYS_.keys():
            address_keys.append(FORM_KEYS_[key])
            address_vals.append(value)
        else:
            event_lines_to_keep.append(line)
    if not address_vals:
        return event_lines
    updated_place = ', '.join(address_vals)
    form = ', '.join(address_keys)
    if place:
        updated_place = place + ', ' + updated_place
        form = 'Other, ' + form
    event_lines_to_keep.append('2 PLAC ' + updated_place + '\n')
    event_lines_to_keep.append('3 FORM ' + form + '\n')
    return event_lines_to_keep


def process_person(person_lines: List[str]) -> List[str]:
    event_lines = []
    updated_event_lines = []
    for line in person_lines:
        if line.startswith('1 '):
            updated_event_lines += process_event(event_lines)
            event_lines = []
        event_lines.append(line)
    updated_event_lines += event_lines
    return updated_event_lines


def process_gedcom(inpath: str, outpath: str):
    person_lines = []
    with open(inpath, 'r') as infile:
        with open(outpath, 'w') as outfile:
            for line in infile:
                if line.startswith('0 ') and line.endswith('INDI\n'):
                    outfile.writelines(process_person(person_lines))
                    person_lines = []
                person_lines.append(line)
            outfile.writelines(person_lines)


if __name__ == '__main__':
    process_gedcom('/Users/xx/Downloads/export-BloodTree-6.ged', '/Users/xx/Downloads/export-BloodTree-6-out.ged')
