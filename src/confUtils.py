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

def check_config(config):
	# Check all section exist
	check_config_section(config, utils.sectionDefault)
	check_config_section(config, utils.imapSubject)
	check_config_section(config, utils.imapFrom)
	check_config_section(config, utils.imapTo)

	# Check all mandatories keys
	check_config_key(config, utils.sectionDefault, utils.hostname)
	check_config_key(config, utils.sectionDefault, utils.port)
	check_config_key(config, utils.sectionDefault, utils.username)
	check_config_key(config, utils.sectionDefault, utils.password)
	check_config_key(config, utils.sectionDefault, utils.mailbox)
	check_config_key(config, utils.sectionDefault, utils.pollingInterval)
	check_config_key(config, utils.sectionDefault, utils.imapDefaultFolder)

def check_config_section(config, section):
	if not config.has_section(section):
		log(ERROR, 'No section "{}" in config file'.format(section))
		sys.exit(1)

def check_config_key(config, section, key):
	if not config.has_option(section, key):
		log(ERROR, 'No key "{}" in section "{}" in config file'.format(key, section))
		sys.exit(1)
