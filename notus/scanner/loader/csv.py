# Copyright (C) 2021 Greenbone Networks GmbH
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ast
import csv
import logging

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..models.advisory import (
    OperatingSystemAdvisories,
    Advisory,
    PackageAdvisories,
)
from ..models.package import parse_rpm_package

from .loader import AdvisoriesLoader

logger = logging.getLogger(__name__)


class CsvAdvisoriesLoader(AdvisoriesLoader):
    def __init__(self, csv_file: Path):
        self._csv_file = csv_file

    def load(self, operating_system: str) -> PackageAdvisories:
        with self._csv_file.open() as raw_csv_file:
            # Skip the license header, so the actual
            # content can be parsed by the DictReader
            for line_string in raw_csv_file:
                if line_string.startswith("{"):
                    break

            reader = csv.DictReader(raw_csv_file)
            for advisory_dict in reader:
                if not "OID" in advisory_dict:
                    # something is wrong with the file
                    logger.error(
                        'No OID found for csv advisory %s', advisory_dict
                    )
                    continue

                if not "VULN_INFO_DICT" in advisory_dict:
                    logger.warning(
                        'Missing vulnerability information for OID %s',
                        advisory_dict['OID'],
                    )
                    continue

                creation_date = datetime.fromtimestamp(
                    int(advisory_dict['CREATION_DATA'])
                )
                last_modification = datetime.fromtimestamp(
                    int(advisory_dict['LAST_MODIFICATION'])
                )
                severity_date = datetime.fromtimestamp(
                    int(advisory_dict['SEVERITY_DATE'])
                )
                vuln_info_dict: Dict[str, List[str]] = ast.literal_eval(
                    advisory_dict["VULN_INFO_DICT"]
                )

                operating_system_advisories = OperatingSystemAdvisories()

                for os_name, package_names in vuln_info_dict.items():
                    package_advisories = PackageAdvisories()

                    advisory = Advisory(
                        oid=advisory_dict['OID'],
                        title=advisory_dict['TITLE'],
                        creation_date=creation_date,
                        last_modification=last_modification,
                        advisory_id=advisory_dict['ADVISORY_ID'],
                        advisory_xref=advisory_dict['ADVISORY_XREF'],
                        severity_origin=advisory_dict['SEVERITY_ORIGIN'],
                        severity_date=severity_date,
                        severity_vector_v2=advisory_dict['SEVERITY_VECTOR_V2'],
                        severity_vector_v3=advisory_dict['SEVERITY_VECTOR_V3'],
                        summary=advisory_dict['SUMMARY'],
                        insight=advisory_dict['INSIGHT'],
                        affected=advisory_dict['AFFECTED'],
                        impact=advisory_dict['IMPACT'],
                    )

                    for package_name in package_names:
                        package = parse_rpm_package(package_name)
                        package_advisories.add_advisory_for_package(
                            package, advisory
                        )

                    operating_system_advisories.set_package_advisories(
                        os_name, package_advisories
                    )

                return operating_system_advisories.get_package_advisories(
                    operating_system
                )
