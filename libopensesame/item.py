#-*- coding:utf-8 -*-

"""
This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""

import openexp.mouse
import openexp.keyboard
from libopensesame.exceptions import osexception
from libopensesame import debug, regexp
import codecs
import string
import os
import sys
import pygame

class item(object):

	"""Abstract class that serves as the basis for all OpenSesame items."""

	encoding = u'utf-8'

	def __init__(self, name, experiment, string=None):

		"""
		Constructor.

		Arguments:
		name 		--	The name of the item.
		experiment 	--	The experiment object.

		Keyword arguments:
		string		--	An definition string. (default=None).
		"""

		self.name = name
		self.experiment = experiment
		self.debug = debug.enabled
		self.count = 0
		# A number of keywords are reserved, which means that they cannot be
		# used as variable names
		self.reserved_words = [u'experiment', u'variables', u'comments', \
			u'item_type']
		for attr in dir(item):
			if hasattr(getattr(item, attr), u'__call__'):
				self.reserved_words.append(attr)
		self._get_lock = None
		# item_type shouldn't be explicitly set anymore.
		if hasattr(self, u'item_type'):
			debug.msg(u'item_type has been set explicitly in item "%s"' % \
			self.name, reason=u'deprecation')
		# Deduce item_type from class name
		prefix = self.experiment.item_prefix()
		self.item_type = unicode(self.__class__.__name__)
		if self.item_type.startswith(prefix):
			self.item_type = self.item_type[len(prefix):]
		if not hasattr(self, u'description'):
			self.description = u'Default description'
		if not hasattr(self, u'round_decimals'):
			self.round_decimals = 2
		self.from_string(string)

	def reset(self):

		"""
		desc:
			Resets all item variables to their default value.
		"""

		pass

	def prepare(self):

		"""Implements the prepare phase of the item."""

		self.time = self.experiment._time_func
		self.sleep = self.experiment._sleep_func
		self.experiment.set(u'count_%s' % self.name, self.count)
		self.count += 1

	def run(self):

		"""Implements the run phase of the item."""

		pass

	def parse_variable(self, line):

		"""
		Reads a single variable from a single definition line.

		Arguments:
		line	--	A single definition line.

		Returns:
		True on succes, False on failure.
		"""

		# It is a little ugly to call parse_comment() here, but otherwise
		# all from_string() derivatives need to be modified
		if self.parse_comment(line):
			return True
		l = self.split(line.strip())
		if len(l) > 0 and l[0] == u'set':
			if len(l) != 3:
				raise osexception( \
					u'Error parsing variable definition: "%s"' % line)
			else:
				self.set(l[1], l[2])
				return True
		return False

	def parse_keywords(self, line, unsanitize=False, _eval=False):

		"""
		Parses keywords, e.g. 'my_keyword=my_value'.

		Arguments:
		line		--	A single definition line.

		Keyword arguments:
		unsanitize	--	DEPRECATED KEYWORD.
		_eval		--	Indicates whether the values should be evaluated.
						(default=False)

		Returns:
		A value dictionary with keywords as keys and values as values.
		"""

		# Parse keywords
		l = self.split(line.strip())
		keywords = {}
		for i in l:
			j = i.find(u'=')
			if j != -1:
				# UGLY HACK: if the string appears to be plain text,
				# rather than a keyword, for example something like
				# 'accuracy = [acc]%', do not parse it as a keyword-
				# value pair. The string needs to occur only once in
				# the full line, both quoted and unquoted.
				q = u'"%s"' % i
				if line.count(q) == 1 and line.count(i) == 1:
					debug.msg( \
						u'"%s" does not appear to be a keyword-value pair in string "%s"' \
						% (i, line))
				else:
					var = str(i[:j])
					val = self.auto_type(i[j+1:])
					if _eval:
						val = self.eval_text(val)
					keywords[var] = val
		return keywords

	def parse_line(self, line):

		"""
		Allows for arbitrary line parsing, for item-specific requirements.

		Arguments:
		line	--	A single definition line.
		"""

		pass

	def parse_comment(self, line):

		"""
		Parses comments from a single definition line, indicated by # // or '.

		Arguments:
		line	--	A single definition line.

		Returns:
		True on succes, False on failure.
		"""

		line = line.strip()
		if len(line) > 0 and line[0] == u'#':
			self.comments.append(line[1:])
			return True
		elif len(line) > 1 and line[0:2] == u'//':
			self.comments.append(line[2:])
			return True
		return False

	def set_response(self, response=None, response_time=None, correct=None):

		"""
		desc:
			Processes a response in such a way that feedback variables are
			updated as well.

		keywords:
			response:
				desc:	The response value.
			response_time:
				desc:	The response time, or None.
				type:	[int, float, NoneType]
			correct:
				desc:	The correctness value, which should be 0, 1, True,
						False, or None.
				type:	[int, bool, NoneType]

		example: |
			from openexp.keyboard import keyboard
			my_keyboard = keyboard(exp)
			t1 = self.time()
			button, timestamp = my_keyboard.get_key()
			if button == 'left':
				correct = 1
			else:
				correct = 0
			rt = timestamp - t1
			self.set_response(response=button, response_time=rt,
				correct=correct)
		"""

		# Handle response variables.
		self.experiment.set(u'total_responses', self.experiment.get( \
			u'total_responses') + 1)
		self.experiment.set(u'response', response)
		self.experiment.set(u'response_time', response_time)
		if response_time != None:
			if type(response_time) not in (int, float):
				raise osexception(u'response should be a numeric value or None')
			self.experiment.set(u'total_response_time', self.experiment.get( \
			u'total_response_time') + self.get(u'response_time'))
		if correct != None:
			if correct not in (0, 1, True, False, None):
				raise osexception( \
					u'correct should be 0, 1, True, False, or None')
			if correct:
				self.experiment.set(u'total_correct', self.experiment.get( \
					u'total_correct') + 1)
				self.experiment.set(u'correct', 1)
			else:
				self.experiment.set(u'correct', 0)
		# Set feedback variables
		self.experiment.set(u'acc', 100.0 * self.experiment.get( \
			u'total_correct') / self.experiment.get(u'total_responses'))
		self.experiment.set(u'avg_rt', self.experiment.get( \
			u'total_response_time') / self.experiment.get(u'total_responses'))
		self.experiment.set(u'accuracy', self.experiment.get(u'acc'))
		self.experiment.set(u'average_response_time', self.experiment.get( \
			u'avg_rt'))
		# Copy the response variables to variables with a name suffix.
		self.experiment.set(u'correct_%s' % self.get(u'name'), \
			self.experiment.get(u'correct'))
		self.experiment.set(u'response_%s' % self.get(u'name'), \
			self.experiment.get(u'response'))
		self.experiment.set(u'response_time_%s' % self.get(u'name'), \
			self.experiment.get(u'response_time'))

	def variable_to_string(self, var):

		"""
		Encodes a variable into a definition string.

		Arguments:
		var		--	The variable to encode.

		Returns:
		A definition string.
		"""

		val = self.unistr(self.variables[var])
		# Multiline variables are stored as a block
		if u'\n' in val or u'"' in val:
			s = u'__%s__\n' % var
			for l in val.split(u'\n'):
				s += '\t%s\n' % l
			while s[-1] in (u'\t', u'\n'):
				s = s[:-1]
			s += u'\n\t__end__\n'
			return s
		# Regular variables
		else:
			return u'set %s "%s"\n' % (var, val)

	def from_string(self, string):

		"""
		desc:
			Parses the item from a definition string.

		arguments:
			string:
				desc:	A definition string, or None to reset the item.
				type:	[str, NoneType]
		"""

		debug.msg()
		textblock_var = None
		self.variables = {}
		self.reset()
		self.comments = []
		if string is None:
			return
		for line in string.split(u'\n'):
			line_stripped = line.strip()
			# The end of a textblock
			if line_stripped == u'__end__':
				if textblock_var == None:
					self.experiment.notify( \
						u'It appears that a textblock has been closed without being opened. The most likely reason is that you have used the string "__end__", which has a special meaning for OpenSesame.')
				else:
					self.set(textblock_var, textblock_val)
					textblock_var = None
			# The beginning of a textblock. A new textblock is only started when
			# a textblock is not already ongoing, and only if the textblock
			# start is of the format __VARNAME__
			elif line_stripped[:2] == u'__' and line_stripped[-2:] == u'__' \
				and textblock_var == None:
				textblock_var = line_stripped[2:-2]
				if textblock_var in self.reserved_words:
					textblock_var = u'_' + textblock_var
				if textblock_var != u'':
					textblock_val = u''
				else:
					textblock_var = None
				# We cannot just strip the multiline code, because that may mess
				# up indentation. So we have to detect if the string is indented
				# based on the opening __varname__ line.
				strip_tab = line[0] == u'\t'
			# Collect the contents of a textblock
			elif textblock_var != None:
				if strip_tab:
					textblock_val += line[1:] + u'\n'
				else:
					textblock_val += line + u'\n'
			# Parse regular variables
			elif not self.parse_variable(line):
				self.parse_line(line)

	def to_string(self, item_type=None):

		"""
		Encodes the item into an OpenSesame definition string.

		Keyword arguments:
		item_type	--	The type of the item or None for autodetect.
						(default=None)

		Returns:
		The unicode definition string
		"""

		if item_type == None:
			item_type = self.item_type
		s = u'define %s %s\n' % (item_type, self.name)
		for comment in self.comments:
			s += u'\t# %s\n' % comment.strip()
		for var in sorted(self.variables):
			s += u'\t' + self.variable_to_string(var)
		return s

	def resolution(self):

		"""
		desc: |
			Returns the display resolution and checks whether the resolution is
			valid.

			__Important note:__

			The meaning of 'resolution' depends on the back-end. For example,
			the legacy back-end changes the actual resolution of the display,
			whereas the other back-ends do not alter the actual display
			resolution, but create a 'virtual display' with the requested
			resolution that is presented in the center of the display.

		returns:
			desc:	A (width, height) tuple
			type:	tuple
		"""

		w = self.get(u'width')
		h = self.get(u'height')
		if type(w) != int or type(h) != int:
			raise osexception( \
				u'(%s, %s) is not a valid resolution' % (w, h))
		return w, h

	def set(self, var, val):

		"""
		desc: |
			Sets an OpenSesame variable.

			If you want to set a variable so that it is available in other items
			as well (such as the logger item, so you can log the variable), you
			need to use the set() function from the experiment. So, in an
			inline_script item you would generally set a variable with
			exp.set(), rather than self.set().

			__Important note:__

			You can only set simple variable types (unicode, float, and int).
			If you use the set function to save another type of variable, it
			will be converted to a unicode representation.

		arguments:
			var:
				desc:	The name of an experimental variable.
				type:	[str, unicode]
			val:
				desc:	A value.

		example: |
			exp.set('my_timestamp', self.time())
		"""

		# Make sure the variable name and the value are of the correct types
		var = self.unistr(var)
		val = self.auto_type(val)
		# Check whether the variable name is valid
		if regexp.sanitize_var_name.sub(u'_', var) != var:
			raise osexception( \
				u'"%s" is not a valid variable name. Variable names must consist of alphanumeric characters and underscores, and may not start with a digit.' \
				% var)
		# Check whether the variable name is not protected
		if var in self.reserved_words:
			raise osexception( \
				u'"%s" is a reserved keyword (i.e. it has a special meaning for OpenSesame), and therefore cannot be used as a variable name. Sorry!' \
				% var)

		# Register the variables
		setattr(self, var, val)
		self.variables[var] = val

	def unset(self, var):

		"""
		desc:
			Unsets (forgets) an OpenSesame variable.

		arguments:
			var:
				desc:	The name of an OpenSesame variable.
				type:	[str, unicode]

		example: |
			self.set('var', 'Hello world!')
			print(self.get('var')) # Prints 'Hello world!'
			self.unset('variable_to_forget')
			print(self.get('var')) # Gives error!
		"""

		var = self.unistr(var)
		if var in self.variables:
			del self.variables[var]
		try:
			delattr(self, var)
		except:
			pass

	def get(self, var, _eval=True):

		"""
		desc: |
			Returns the value of an OpenSesame variable. Checks first if the
			variable exists 'locally' in the item and, if not, checks if the
			variable exists 'globally' in the experiment.

			The type of the returned value can be int, float, or unicode
			(string). The appropriate type is automatically selected, e.g. '10'
			is returned as int, '10.1' as float, and 'some text' as unicode.

			The _eval parameter is used to specify whether the value of the
			variable should be evaluated, in case it contains references to
			other variables. This is best illustrated by example 2 below.

		arguments:
			var:
				desc:	The name of an OpenSesame variable.
				type:	[str, unicode]

		keywords:
			_eval:
				desc:	Indicates whether the variable should be evaluated, i.e.
						whether containing variables should be processed.
				type:	bool

		returns:
			desc:	The value.
			type:	[unicode, int, float]

		example: |
			# Example 1
			if self.get('cue') == 'valid':
				print('This is a validly cued trial')

			# Example 2
			exp.set('var1', 'I like [var2]')
			exp.set('var2', 'OpenSesame')
			print(self.get('var1')) # prints 'I like OpenSesame'
			print(self.get('var1', _eval=False)) # prints 'I like [var2]'
		"""

		var = self.unistr(var)
		# Avoid recursion
		if var == self._get_lock:
			raise osexception( \
				u"Recursion detected! Is variable '%s' defined in terms of itself (e.g., 'var = [var]') in item '%s'" \
				% (var, self.name))
		# Get the variable
		if hasattr(self, var):
			val = getattr(self, var)
		else:
			try:
				val = getattr(self.experiment, var)
			except:
				raise osexception( \
					u"Variable '%s' is not set in item '%s'.<br /><br />You are trying to use a variable that does not exist. Make sure that you have spelled and capitalized the variable name correctly. You may wish to use the variable inspector (Control + I) to find the intended variable." \
					% (var, self.name))
		if _eval:
			# Lock to avoid recursion and start evaluating possible variables
			self._get_lock = var
			val = self.eval_text(val)
			self._get_lock = None
			# Done!
		return val

	def get_check(self, var, default=None, valid=None, _eval=True):

		"""
		desc:
			Similar to get(), but falls back to a default if the variable has
			not been set. It also raises an error if the value is not part of
			the valid list.

		arguments:
			var:
				desc:	The name of an OpenSesame variable
				type:	[unicode, str]

		keywords:
			default:
				desc:	A default 'fallback' value or None for no fallback, in
						which case an exception is rased if the variable does
						not exist.
				type:	[unicode, float, int]
			valid:
				desc:	A list of allowed values (or None for no restrictions).
						An exception is raised if the value is not an allowed
						value.
				type:	[list, NoneType]
			_eval:
				desc:	Indicates whether the variable should be evaluated, i.e.
						whether containing variables should be processed.
				type:	bool

		returns:
			desc:	The value
			type:	[unicode, float, int]

		example: |
			if self.get_check('cue', default='invalid') == 'valid':
				print('This is a validly-cued trial')
		"""

		if default == None:
			val = self.get(var, _eval=_eval)
		elif self.has(var):
			val = self.get(var, _eval=_eval)
		else:
			val = default
		if valid != None and val not in valid:
			raise osexception( \
				u"Variable '%s' is '%s', expecting '%s'" % (var, val, \
				u" or ".join(valid)))
		return val

	def has(self, var):

		"""
		desc:
			Checks if an OpenSesame variable exists, either in the item or in
			the experiment.

		arguments:
			var:
				desc:	The name of an OpenSesame variable.
				type:	[str, unicode]

		returns:
			desc:	True if the variable exists, False if not.
			type:	bool

		example: |
			if not self.has('response'):
				print('No response has been collected yet')
		"""

		var = self.unistr(var)
		return hasattr(self, var) or hasattr(self.experiment, var)

	def get_refs(self, text):

		"""
		desc:
			Returns a list of variables that are referred to by a string of
			text.

		arguments:
			text:
				desc:	A string of text. This can be any type, but will coerced
						to unicode if it is not unicode.

		returns:
			desc:	A list of variable names or an empty list if the string
					contains no references.
			type:	list

		Example: |
			print(self.get_refs('There are [two] [references] here'))
			# Prints ['two', 'references']
		"""

		text = self.unistr(text)

		l = []
		start = -1
		while True:
			# Find the start and end of a variable definition
			start = text.find(u'[', start + 1)
			if start < 0:
				break
			end = text.find(u']', start + 1)
			if end < 0:
				raise osexception( \
					u"Missing closing bracket ']' in string '%s', in item '%s'" \
					% (text, self.name))
			var = text[start+1:end]
			l.append(var)
			var = var[end:]
		return l

	def auto_type(self, val):

		"""
		desc:
			Converts a value into the 'best fitting' or 'simplest' type that is
			compatible with the value.

		arguments:
			val:
				desc:	A value. This can be any type.

		returns:
			desc:	The same value converted to the 'best fitting' type.
			type:	[unicode, int, float]

		Example: |
			print(type(self.auto_type('1'))) # Prints 'int'
			print(type(self.auto_type('1.1'))) # Prints 'float'
			print(type(self.auto_type('some text'))) # Prints 'unicode'
			# Note: Boolean values are converted to 'yes' / 'no' and are
			# therefore also returned as unicode objects.
			print(type(self.auto_type(True))) # Prints 'unicode'
		"""

		# Booleans are converted to True/ False
		if type(val) == bool:
			if val:
				return u'yes'
			else:
				return u'no'
		# Try to convert the value to a numeric type
		try:
			# Check if the value can be converted to an int without loosing
			# precision. If so, convert to int
			if int(float(val)) == float(val):
				return int(float(val))
			# Else convert to float
			else:
				return float(val)
		except:
			# Else, fall back to unicde
			return self.unistr(val)

	def set_item_onset(self, time=None):

		"""
		Set a timestamp for the item's executions

		Keyword arguments:
		time -- the timestamp or None to use the current time (default = None)
		"""

		if time == None:
			time = self.time()
		setattr(self.experiment, u'time_%s' % self.name, time)

	def dummy(self, **args):

		"""
		Dummy function

		Keyword arguments:
		arguments -- accepts all keywords for compatibility
		"""

		pass

	def eval_text(self, text, round_float=False, soft_ignore=False,
		quote_str=False):

		"""
		desc:
			Evaluates a string of text, so that all variable references (e.g.,
			'[var]') are replaced by values.

		arguments:
			text:
				desc:	The text to be evaluated. This can be any type, but only
						str and unicode types will be evaluated.

		keywords:
			round_float:
				desc:	A Boolean indicating whether float values should be
						rounded to a precision of [round_decimals].
						round_decimals is an OpenSesame variable that has a
						default value of 2.
				type:	bool
			soft_ignore:
				desc:		A Boolean indicating whether missing variables
							should be ignored, rather than cause an exception.
				type:		bool
			quote_str:
				desc:		A Boolean indicating whether string variables should
							be surrounded by single quotes (default=False).
				type:		bool

		returns:
			desc:	The evaluated text.
			type:	[unicode, int, float]

		example: |
			exp.set('var', 'evaluated')
			print(self.eval_text('This string has been [var]'))
			# Prints 'This string has been evaluated
		"""

		# Only unicode needs to be evaluated
		text = self.auto_type(text)
		if type(text) != unicode:
			return text

		# Prepare a template for rounding floats
		if round_float:
			float_template = u'%%.%sf' % self.get("round_decimals")
		# Find and replace all variables in the text
		while True:
			m = regexp.find_variable.search(text)
			if m == None:
				break
			var = m.group(0)[1:-1]
			if not soft_ignore or self.has(var):
				val = self.get(var)
				# Quote strings if necessary
				if type(val) == unicode and quote_str:
					val = u"'" + val + u"'"
				# Round floats
				elif round_float and type(val) == float:
					val = float_template % val
				else:
					val = self.unistr(val)
				text = text.replace(m.group(0), val, 1)
		return self.auto_type(text)

	def compile_cond(self, cond, bytecode=True):

		"""
		Create Python code for a given conditional statement.

		Arguments:
		cond		--	The conditional statement (e.g., '[correct] = 1')

		Keyword arguments:
		bytecode	--	A boolean indicating whether the generated code should
						be byte compiled (default=True).

		Returns:
		Python code (possibly byte compiled) that reflects the conditional
		statement.
		"""

		src = cond

		# If the conditional statement is preceded by a '=', it is interpreted as
		# Python code, like 'self.get("correct") == 1'. In this case we only have
		# to strip the preceding space
		if len(src) > 0 and src[0] == u'=':
			code = src[1:]
			debug.msg(u'Python-style conditional statement: %s' % code)

		# Otherwise, it is interpreted as a traditional run if statement, like
		# '[correct] = 1'
		else:
			operators = u"!=", u"==", u"=", u"<", u">", u">=", u"<=", u"+", \
				u"-", u"(", u")", u"/", u"*", u"%", u"~", u"**", u"^"
			op_chars = u"!", u"=", u"=", u"<", u">", u"+", u"-", u"(", u")", \
				u"/", u"*", u"%", u"~", u"*", u"^"
			whitespace = u" ", u"\t", u"\n"
			keywords = u"and", u"or", u"is", u"not", u"true", u"false"
			capitalize = u"true", u"false", u"none"

			# Try to fix missing spaces
			redo = True
			while redo:
				redo = False
				for i in range(len(cond)):
					if cond[i] in op_chars:
						if i != 0 and cond[i-1] not in op_chars + whitespace:
							cond = cond[:i] + u" " + cond[i:]
							redo = True
							break
						if i < len(cond)-1 and cond[i+1] not in \
							op_chars+whitespace:
							cond = cond[:i+1] + u" " + cond[i+1:]
							redo = True
							break

			# Rebuild the conditional string
			l = []
			i = 0
			for word in self.split(cond):
				if len(word) > 2 and word[0] == u"[" and word[-1] == u"]":
					l.append(u"self.get(u'%s')" % word[1:-1])
				elif word == u"=":
					l.append(u"==")
				elif word.lower() == u"always":
					l.append(u"True")
				elif word.lower() == u"never":
					l.append(u"False")
				elif word.lower() in operators + keywords:
					if word.lower() in capitalize:
						l.append(word.capitalize())
					else:
						l.append(word.lower())
				else:
					val = self.auto_type(word)
					if type(val) == unicode:
						l.append(u"u\"%s\"" % word)
					else:
						l.append(self.unistr(word))
				i += 1

			code = u" ".join(l)
			if code != u"True":
				debug.msg(u"'%s' => '%s'" % (src, code))

		# Optionally compile the conditional statement to bytecode and return
		if not bytecode:
			return code
		try:
			bytecode = compile(code, u"<conditional statement>", u"eval")
		except:
			raise osexception( \
				u"'%s' is not a valid conditional statement in sequence item '%s'" \
				% (cond, self.name))
		return bytecode

	def var_info(self):

		"""
		Give a list of dictionaries with variable descriptions

		Returns:
		A list of (variable, description) tuples
		"""

		return [ (u"time_%s" % self.name, u"[Timestamp of last item call]"), \
			(u"count_%s" % self.name, u"[Number of item calls]") ]

	def sanitize(self, s, strict=False, allow_vars=True):

		"""
		desc:
			Removes invalid characters (notably quotes) from the string.

		arguments:
			s:
				desc:	The string to be sanitized. This can be any type, but
						if it is not unicode, it will be coerced to unicode.

		keywords:
			strict:
				desc:	If True, all except underscores and alphanumeric
						characters are stripped.
				type:	bool
			allow_vars:
				desc:	If True, square brackets are not sanitized, so you can
						use variables.
				type:	bool

		returns:
			desc:	A sanitized string.
			type:	unicode

		example: |
			# Prints 'Universit Aix-Marseille'
			print(self.sanitize('\"Université Aix-Marseille\"'))
			# Prints 'UniversitAixMarseille'
			print(self.sanitize('\"Université Aix-Marseille\""', strict=True))
		"""

		s = self.unistr(s)
		if strict:
			if allow_vars:
				return regexp.sanitize_strict_vars.sub(u'', s)
			return regexp.sanitize_strict_novars.sub(u'', s)
		return regexp.sanitize_loose.sub(u'', s)

	def usanitize(self, s, strict=False):

		"""
		desc:
			Converts all non-ASCII characters to U+XXXX notation, so that the
			resulting string can be treated as plain ASCII text.

		arguments:
			s:
				desc:	A unicode string to be santized
				type:	unicode

		keywords:
			strict:
				desc:	If True, special characters are ignored rather than
						recoded.
				type:	bool

		returns:
			desc:	A regular Python string with all special characters replaced
					by U+XXXX notation or ignored (if strict).
			type:	str
		"""

		if strict:
			_s = codecs.encode(s, u'ascii', u'ignore')
		else:
			_s = codecs.encode(s, u'ascii', u'osreplace')
		_s = str(_s)
		return _s.replace(os.linesep, '\n')

	def unsanitize(self, s):

		"""
		Converts the U+XXXX notation back to actual Unicode encoding

		Arguments:
		s -- a regular string to be unsanitized

		Returns:
		A unicode string with special characters
		"""

		if not isinstance(s, basestring):
			raise osexception( \
			u'unsanitize() expects first argument to be unicode or str, not "%s"' \
			% type(s))
		s = self.unistr(s)
		while True:
			m = regexp.unsanitize.search(s)
			if m == None:
				break
			s = s.replace(m.group(0), unichr(int(m.group(1), 16)), 1)
		return s

	def unistr(self, val):

		"""
		desc: |
			Converts a value to a unicode string. This function is mostly
			necessary to make sure that normal strings with special characters
			are correctly encoded into unicode, and don't result in TypeErrors.

			The conversion logic is as follows:

			- unicode values are returned unchanged.
			- str values are decoded using utf-8.
			- all other types are typecast to unicode, assuming utf-8 encoding
			  where applicable.

		arguments:
			val:
				desc:	A value of any type.

		returns:
			desc:	A unicode string.
			type:	unicode
		"""

		# Unicode strings cannot (and need not) be encoded again
		if isinstance(val, unicode):
			return val
		# Regular strings need to be encoded using the correct encoding
		if isinstance(val, str):
			return unicode(val, encoding=self.encoding, errors=u'replace')
		# Numeric values are encoded right away
		if isinstance(val, int) or isinstance(val, float):
			return unicode(val)
		# Some types need to be converted to unicode, but require the encoding
		# and errors parameters. Notable examples are Exceptions, which have
		# strange characters under some locales, such as French. It even appears
		# that, at least in some cases, they have to be encodeed to str first.
		# Presumably, there is a better way to do this, but for now this at
		# least gives sensible results.
		try:
			return unicode(str(val), encoding=self.encoding, errors=u'replace')
		except:
			pass
		# For other types, the unicode representation doesn't require a specific
		# encoding. This mostly applies to non-stringy things, such as integers.
		return unicode(val)

	def split(self, u):

		"""
		Splits a unicode string in the same way as shlex.split(). Unfortunately,
		shlex doesn't handle unicode properly, so this wrapper function is
		required.

		Arguments:
		u -- a unicode string

		Returns:
		A list of unicode strings, split as described here:
		http://docs.python.org/library/shlex.html#shlex.split
		"""

		import shlex
		try:
			return [chunk.decode(self.encoding) for chunk in shlex.split( \
				u.encode(self.encoding))]
		except Exception as e:
			raise osexception( \
				u'Failed to parse line "%s". Is there a closing quotation missing?' \
				% u, exception=e)

	def color_check(self, col):

		"""
		desc:
			Checks whether a string is a valid color name. Raises an exception
			if `col` is not a valid color.

		arguments:
			col:	The color to check.

		example: |
			# Ok
			print(self.color_check('red'))
			# Ok
			print(self.color_check('#FFFFFF'))
			# Raises osexception
			print(self.color_check('this is not a color'))
		"""

		try:
			if type(col) == unicode:
				col = str(col)
			pygame.Color(col)
		except Exception as e:
			raise osexception( \
				u"'%s' is not a valid color. See http://www.w3schools.com/html/html_colornames.asp for an overview of valid color names" \
				% self.unistr(col), exception=e)

	def sleep(self, ms):

		"""
		desc:
			Sleeps for a specified duration.

		arguments:
			ms:
				desc:	An value specifying the duration in milliseconds.
				type:	[int, float]

		example: |
			self.sleep(1000) # Sleeps one second
		"""

		# This function is set by item.prepare()
		raise osexception( \
			u'item.sleep(): This function should be set by the canvas backend.')

	def time(self):

		"""
		desc:
			Returns a timestamp for the current time. This timestamp only has
			a relative meaning, i.e. you can use it to determine the interval
			between two moments, but not the actual time. Whether the timestamp
			is a `float` or `int` depends on the back-end.

		returns:
			desc:	A timestamp of the current time.
			type:	[int, float]

		example: |
			print('The time is %s' % self.time())
		"""

		# This function is set by item.prepare()
		raise osexception( \
			u"item.time(): This function should be set by the canvas backend.")

	def log(self, msg):

		"""
		desc:
			Writes a message to the log file. Note that using the `log()`
			function in combination with a logger item may result in messy log
			files.

		arguments:
			msg:
				desc:	A message. This can be any type and will we be converted
						to a unicode string using the logic described in
						[unistr].

		example: |
			self.log('TIMESTAMP = %s' % self.time())
		"""

		self.experiment._log.write(u'%s\n' % self.unistr(msg))

	def flush_log(self):

		"""
		desc:
			Forces any pending write operations to the log file to be written to
			disk.

		example: |
			self.log('TRIAL FINISHED')
			self.flush_log()
		"""

		self.experiment._log.flush()
		os.fsync(self.experiment._log)

def osreplace(exc):

	"""
	desc:
		A replacement function to allow opensame-style replacement of unicode
		characters.

	arguments:
		exc:
			type:	UnicodeEncodeError

	returns:
		desc:	A (replacement, end) tuple.
		type:	tuple
	"""

	_s = u''
	for ch in exc.object[exc.start:exc.end]:
		_s += u'U+%.4X' % ord(ch)
	return _s, exc.end

codecs.register_error(u'osreplace', osreplace)
