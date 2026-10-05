#!/usr/bin/env python3
"""Convert the live-smoke JSON report into JUnit XML."""
import json
import sys
import xml.etree.ElementTree as ET

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as fh:
    report = json.load(fh)

cases = []
for name, result in report.items():
    failed = (name == "load_test" and result.get("failures", 0) > 0) or result.get("status") == "failed"
    cases.append((name, failed, json.dumps(result, ensure_ascii=False)))

suite = ET.Element("testsuite", name="live-smoke", tests=str(len(cases)),
                   failures=str(sum(1 for _, failed, _ in cases if failed)))
for name, failed, detail in cases:
    case = ET.SubElement(suite, "testcase", name=name)
    if failed:
        failure = ET.SubElement(case, "failure", message="live smoke failed")
        failure.text = detail
    else:
        output = ET.SubElement(case, "system-out")
        output.text = detail

ET.ElementTree(suite).write(dst, encoding="utf-8", xml_declaration=True)
