'''
confUtils.py: useful and general methods for the configuration.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import ConfigParser
import sys
import utils
from logger import log, ERROR, WARN, INFO, DEBUG

def checkConfig(config):
	# Check all section exist
	checkConfigSection(config, utils.sectionDefault)
	checkConfigSection(config, utils.imapSubject)
	checkConfigSection(config, utils.imapFrom)
	checkConfigSection(config, utils.imapTo)

	# Check all mandatories keys
	checkConfigKey(config, utils.sectionDefault, utils.hostname)
	checkConfigKey(config, utils.sectionDefault, utils.port)
	checkConfigKey(config, utils.sectionDefault, utils.username)
	checkConfigKey(config, utils.sectionDefault, utils.password)
	checkConfigKey(config, utils.sectionDefault, utils.mailbox)
	checkConfigKey(config, utils.sectionDefault, utils.pollingInterval)
	checkConfigKey(config, utils.sectionDefault, utils.imapDefaultFolder)

def checkConfigSection(config, section):
	if not config.has_section(section):
		log(ERROR, 'No section "{}" in config file'.format(section))
		sys.exit(1)

def checkConfigKey(config, section, key):
	if not config.has_option(section, key):
		log(ERROR, 'No key "{}" in section "{}" in config file'.format(key, section))
		sys.exit(1)
