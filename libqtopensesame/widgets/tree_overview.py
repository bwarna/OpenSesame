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

from PyQt4 import QtCore, QtGui
from libqtopensesame.misc.config import cfg
from libqtopensesame.misc import _
from libqtopensesame.misc import drag_and_drop
from libqtopensesame.misc.base_subcomponent import base_subcomponent
from libqtopensesame.widgets.tree_append_button import tree_append_button
from libqtopensesame._input.popup_menu import popup_menu
from libopensesame import debug
from libopensesame.exceptions import osexception
from libopensesame.sequence import sequence

class tree_overview(base_subcomponent, QtGui.QTreeWidget):

	"""
	desc:
		A tree widget used in sequence items and the overview area.
	"""

	structure_change = QtCore.pyqtSignal()
	text_change = QtCore.pyqtSignal()

	def __init__(self, main_window, overview_mode=True):

		"""
		desc:
			Constructor.

		arguments:
			main_window:
				desc:		The main window object.
				type:		qtopensesame

		keywords:
			overview_mode:
				desc:		Indicates whether the tree should be overview-area
							style (True) or sequence style (False).
				type:		int
		"""

		super(tree_overview, self).__init__(main_window)
		self.locked = False
		self.overview_mode = overview_mode
		self.setAcceptDrops(True)
		if self.overview_mode:
			self.setHeaderHidden(True)
		else:
			self.setHeaderHidden(False)
			self.setHeaderLabels([_(u'Item name'), _(u'Run if')])
		self.setAlternatingRowColors(True)
		self.itemChanged.connect(self.text_edited)
		self.pending_drag_data = None
		self.drag_timer = None
		if not self.overview_mode:
			self.shortcut_edit_runif = QtGui.QShortcut(
				QtGui.QKeySequence(cfg.shortcut_edit_runif), self,
				self.start_edit_runif,
				context=QtCore.Qt.WidgetWithChildrenShortcut)
			self.append_button = tree_append_button(self)
		else:
			self.append_button = None
		self.shortcut_rename = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_rename), self,
			self.start_rename,
			context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_copy_item = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_copy_clipboard), self,
			self.copy_item, context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_paste_item = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_paste_clipboard), self,
			self.paste_item, context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_delete_item = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_delete), self, self.delete_item,
			context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_delete_item = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_permanently_delete), self,
			self.permanently_delete_item,
			context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_linked_copy = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_linked_copy), self,
			self.create_linked_copy,
			context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.shortcut_unlinked_copy = QtGui.QShortcut(
			QtGui.QKeySequence(cfg.shortcut_unlinked_copy), self,
			self.create_unlinked_copy,
			context=QtCore.Qt.WidgetWithChildrenShortcut)
		self.drop_indicator = None
		self.drop_indicator_pen = QtGui.QPen(QtGui.QBrush(
			QtGui.QColor(u'#73d216')), 2, QtCore.Qt.SolidLine)

	def copy_item(self):

		"""
		desc:
			Copies the currently selected treeitem to the clipboard (if
			supported by the treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.copy()

	def paste_item(self):

		"""
		desc:
			Pastes the clipboard onto the currently selected treeitem (if
			supported by the treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.paste()

	def delete_item(self):

		"""
		desc:
			Deletes the currently selected treeitem (if supported by the
			treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.delete()

	def permanently_delete_item(self):

		"""
		desc:
			Permanently deletes the currently selected treeitem (if supported by
			the treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.permanently_delete()

	def create_linked_copy(self):

		"""
		desc:
			Creates a linked copy of the currently selected item (if supported
			by the treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.create_linked_copy()

	def create_unlinked_copy(self):

		"""
		desc:
			Creates an unlinked copy of the currently selected item (if
			supported by the treeitem).
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			target_treeitem.create_unlinked_copy()

	def select_item(self, name):

		"""
		desc:
			Selects all items that match the specified name.

		arguments:
			name:	The name to select.
		"""

		self.clearSelection()
		l = self.findItems(name,
			QtCore.Qt.MatchFixedString|QtCore.Qt.MatchRecursive, 0)
		if len(l) == 0:
			return
		for _l in l:
			_l.setSelected(True)
		self.experiment.items[name].open_tab(select_in_tree=False)

	def text_edited(self, treeitem, col):

		"""
		desc:
			Processes edits to the item names and run-if statements.

		arguments:
			treeitem:
				desc:	A tree item
				type:	QTreeWidgetItem
			col:
				desc:	The column that was edited.
				type:	int
		"""

		if col == 0:
			if hasattr(treeitem, u'name'):
				from_name = treeitem.name
				to_name = unicode(treeitem.text(0))
				to_name = self.experiment.items.rename(from_name, to_name)
				if to_name == None:
					self.itemChanged.disconnect()
					treeitem.setText(0, from_name)
					self.itemChanged.connect(self.text_edited)
				if from_name != to_name:
					self.itemChanged.disconnect()
					treeitem.setText(0, to_name)
					self.itemChanged.connect(self.text_edited)
				treeitem.name = to_name
				self.text_change.emit()
		elif col == 1:
			if hasattr(treeitem, u'ancestry'):
				parent_item_name, ancestry = treeitem.ancestry()
				parent_item_name, index = self.parent_from_ancestry(ancestry)
				parent_item = self.experiment.items[parent_item_name]
				if parent_item.item_type == u'sequence':
					cond = unicode(treeitem.text(1))
					if cond.strip() == u'':
						cond = u'always'
					cond = parent_item.clean_cond(cond)
					parent_item.set_run_if(index, cond)
					self.itemChanged.disconnect()
					treeitem.setText(1, cond)
					self.itemChanged.connect(self.text_edited)
				self.text_change.emit()

	def mousePressEvent(self, e):

		"""
		desc:
			Initiates a drag event after a mouse press, these are used to
			implement item moving, shallow copying, and deep copying.

		arguments:
			e:
				desc:	A mouse event.
				type:	QMouseEvent
		"""

		super(tree_overview, self).mousePressEvent(e)
		if e.buttons() != QtCore.Qt.LeftButton:
			return
		# Get item and open tab.
		target_treeitem = self.itemAt(e.pos())
		if target_treeitem == None:
			return
		if self.overview_mode:
			target_treeitem.open_tab()
		# Only start drags for draggable tree items.
		if not self.draggable(target_treeitem):
			e.ignore()
			return
		# Get the target item
		target_item_name, target_item_ancestry = target_treeitem.ancestry()
		target_item = self.experiment.items[target_item_name]
		data = 	{
				u'item-name'		: target_item.name,
				u'item-type'		: target_item.item_type,
				u'ancestry'			: target_item_ancestry,
				u'script'			: target_item.to_string(),
				u'application-id'	: self.main_window._id()
				}
		if (QtCore.Qt.ControlModifier & e.modifiers()) and \
			(QtCore.Qt.ShiftModifier & e.modifiers()):
			data[u'type'] = u'item-new'
		else:
			data[u'type'] = u'item-existing'
		# Drags are not started right away, but only after the mouse has been
		# pressed for a minimum interval. To accomplish this, we set a timer,
		# and cancel the timer when the mouse cursor is released.
		if self.drag_timer != None:
			self.drag_timer.stop()
		self.pending_drag_data = data
		self.drag_timer = QtCore.QTimer()
		self.drag_timer.setSingleShot(True)
		self.drag_timer.setInterval(cfg.start_drag_delay)
		self.drag_timer.timeout.connect(self.start_drag)
		self.drag_timer.start()

	def start_drag(self):

		"""
		desc:
			Starts a pending drag operation (if any).
		"""

		if self.pending_drag_data == None:
			return
		drag_and_drop.send(self, self.pending_drag_data)
		self.end_drag()
		self.pending_drag_data = None

	def end_drag(self):

		"""
		desc:
			Ends a drag operation.
		"""

		self.drop_indicator = None
		self.viewport().update()

	def mouseReleaseEvent(self, e):

		"""
		desc:
			Cancels pending drag operations when the mouse is released to
			quickly. This avoids accidental dragging.

		arguments:
			e:
				desc:	A mouse event.
				type:	QMouseEvent
		"""

		super(tree_overview, self).mouseReleaseEvent(e)
		self.pending_drag_data = None

	def parent_from_ancestry(self, ancestry):

		"""
		desc:
			Gets the parent item, and the index of the item in the parent, based
			on an item's ancestry, as returned by ancestry_from_treeitem.

		arguments:
			ancestry:
				desc:	An ancestry string.
				type:	unicode

		returns:
			desc:	A (parent item name, index) tuple.
			type:	tuple
		"""

		l = ancestry.split(u'.')
		if len(l) == 1:
			return None, None
		parent_item_name = l[1].split(u':')[0]
		index = int(l[0].split(u':')[1])
		return parent_item_name, index

	def droppable(self, treeitem, data):

		"""
		desc:
			Determines if a tree item is able to accept drops.

		arguments:
			treeitem:
				desc:	A tree item.
				type:	QTreeWidgetItem
			data:
				desc:	Drag-and-drop data.
				type:	dict

		returns:
			desc:	A bool indicating if the tree item is droppable.
			type:	bool
		"""

		return treeitem != None and treeitem.droppable(data)

	def draggable(self, treeitem):

		"""
		desc:
			Determines if a tree item can be dragged.

		arguments:
			treeitem:
				desc:	A tree item.
				type:	QTreeWidgetItem

		returns:
			desc:	A bool indicating if the tree item is draggable.
			type:	bool
		"""

		return treeitem != None and treeitem.draggable()

	def drop_event_item_move(self, data, e):

		"""
		desc:
			Handles drop events for item moves.

		arguments:
			data:
				desc:	A drop-data dictionary.
				type:	dict:
			e:
				desc:	A drop event.
				type:	QDropEvent
		"""

		if not drag_and_drop.matches(data, [u'item-existing']):
			e.ignore()
			return
		target_treeitem = self.itemAt(e.pos())
		if not self.droppable(target_treeitem, data):
			debug.msg(u'Drop ignored: target not droppable')
			self.main_window.set_status(
				_(u'Drop cancelled: Target not droppable'))
			e.ignore()
			return
		# If the drop comes from this application, check for recursion etc.
		if data[u'application-id'] == self.main_window._id():
			target_item_name, target_item_ancestry = target_treeitem.ancestry()
			item_name = data[u'item-name']
			item = self.experiment.items[item_name]
			if target_item_name in item.children():
				debug.msg(u'Drop ignored: recursion prevented')
				self.main_window.set_status(
					_(u'Drop cancelled: Recursion prevented'))
				e.ignore()
				return
			parent_item_name, index = self.parent_from_ancestry(
				data[u'ancestry'])
			if parent_item_name == None:
				debug.msg(u'Drop ignored: no parent')
				e.ignore()
				return
		# The logic below is a bit complicated, but works as follows:
		# - If we're in a move action, remove the dragged item from its parent,
		#   and set need_restore so that we know this happened.
		# - Try to drop the dragged item onto the target item
		# - If the drop action was unsuccesful, and if need_restore is set,
		#   re-add the dragged item to its former parent.
		need_restore = False
		if not QtCore.Qt.ControlModifier & e.keyboardModifiers() and \
			data[u'application-id'] == self.main_window._id():
			if parent_item_name not in self.experiment.items:
				debug.msg(u'Don\'t know how to remove item from %s' \
					% parent_item_name)
			else:
				self.locked = True
				need_restore = True
				self.experiment.items[parent_item_name].remove_child_item(
					item_name, index)
				self.locked = False
		if self.drop_event_item_new(data, e, target_treeitem=target_treeitem):
			return
		if need_restore:
			self.experiment.items[parent_item_name].insert_child_item(
				item_name, index)
			self.experiment.build_item_tree()

	def drop_event_item_new(self, data, e=None, target_treeitem=None):

		"""
		desc:
			Handles drop events for item creation.

		arguments:
			data:
				desc:	A drop-data dictionary.
				type:	dict:

		keywords:
			e:
				desc:	A drop event or None if a target treeitem is provided.
				type:	[QDropEvent, NoneType]
			target_treeitem:
				desc:	A target tree item or None in a drop event is specified.
				type:	[tree_base_item, NoneType]

		returns:
			desc:	True if the drop was successful, False otherwise.
			type:	bool
		"""

		self.main_window.set_busy(True)
		if not drag_and_drop.matches(data, [u'item-existing', u'item-new']):
			if e != None:
				e.ignore()
			self.main_window.set_busy(False)
			return False
		# Ignore drops on non-droppable tree items.
		if target_treeitem == None:
			target_treeitem = self.itemAt(e.pos())
		if not self.droppable(target_treeitem, data):
			if e != None:
				e.ignore()
			self.main_window.set_busy(False)
			return False
		# Accept drops on the unused items bin and unused items (i.e. items
		# in the bin)
		if target_treeitem.name == u'__unused__' or \
			(target_treeitem.parent() is not None and \
			target_treeitem.parent().name == u'__unused__'):			
			e.accept()
			self.structure_change.emit()
			self.main_window.set_busy(False)
			return True
		# Get the target item, check if it exists, and, if so, drop the source
		# item on it.
		target_item_name = unicode(target_treeitem.text(0))
		if target_item_name not in self.experiment.items:
			debug.msg(u'Don\'t know how to drop on %s' % target_item_name)
			if e != None:
				e.ignore()
			self.structure_change.emit()
			self.main_window.set_busy(False)
			return False
		target_item = self.experiment.items[target_item_name]
		# Get the item to be inserted. If the drop type is item-new, we need
		# to create a new item, otherwise we get an existin item. Also, if
		# the drop doesn't originate from this application, we create a new
		# item.
		if data[u'type'] == u'item-new' \
			or data[u'application-id'] != self.main_window._id():
			try:
				item = self.experiment.items.new(data[u'item-type'],
					data[u'item-name'], data[u'script'])
			except Exception as ex:
				if not isinstance(e, osexception):
					ex = osexception(msg=u'Plug-in error', exception=ex)
				self.notify(
					u'Failed to load plug-in %s (see debug window for stack trace)' \
					% data[u'item-type'])
				self.main_window.print_debug_window(ex)
				e.accept()
				self.main_window.set_busy(False)
				return False
			self.extension_manager.fire(u'new_item',
				name=data[u'item-name'], _type=data[u'item-type'])
		else:
			item = self.experiment.items[data[u'item-name']]

		inserted = False
		# If the item has no parent or if it is the experiment starting point,
		# we insert into it directly.
		if target_treeitem.parent() == None or \
			target_item.name == self.experiment.start:
			target_item.insert_child_item(item.name)
			inserted = True
		else:
			if target_item.item_type in (u'loop', u'sequence'):
				self.main_window.set_busy(False)
				# Choose appropriate option
				if target_item.item_type == u'loop':
					question = _('Set as item to run for %s') % target_item.name
					icon = u'os-loop'
				else:
					question = _('Insert into %s') % target_item.name
					icon = u'os-sequence'
				resp = popup_menu(self, [(0, question, icon),
					(1, _('Insert after %s' % target_item.name), 'list-add')
					]).show()
				# Confirmation
				if resp == 0 and target_item.item_type == u'loop' and \
					target_item.item in self.experiment.items:
					resp = popup_menu(self, [(0, _(u'I know, do it!'), icon)],
						title=_(u'This will replace %s' % (target_item.item))
						).show()
				# If the popup was cancelled
				if resp == None:
					e.accept()
					# Delete the item if it was new or didn't originate from
					# this application.
					if data[u'type'] == u'item-new' \
						or data[u'application-id'] != self.main_window._id():
						del self.experiment.items[item.name]
					self.main_window.set_busy(False)
					return False
				# If the user chose to insert into the target item
				if resp == 0:
					target_item.insert_child_item(item.name)
					inserted = True
		# Otherwise, we find the parent of the target item, and insert the
		# new item at the correct position.
		if not inserted:
			while True:
				try:
					parent_treeitem = target_treeitem.parent()
				except:
					# A race condition can occur in which the tree_overview has
					# been rebuild, thus destroying target_treeitem. If this
					# happens, we re-take target_treeitem based on the mouse
					# coordinates.
					target_treeitem = self.itemAt(e.pos())
					parent_treeitem = target_treeitem.parent()
				if parent_treeitem == None:
					e.accept()
					del self.experiment.items[item.name]
					self.main_window.set_busy(False)
					return False
				parent_item_name = unicode(parent_treeitem.text(0))
				parent_item = self.experiment.items[parent_item_name]
				if isinstance(parent_item, sequence):
					break
				target_treeitem = parent_treeitem
			index = parent_treeitem.indexOfChild(target_treeitem)+1
			parent_item.insert_child_item(item.name, index=index)
		if e != None:
			e.accept()
		self.structure_change.emit()
		if self.overview_mode:
			item.open_tab()
		self.main_window.set_busy(False)
		return True

	def dropEvent(self, e):

		"""
		desc:
			Handles drop events for file opening and item creation.

		arguments:
			e:
				desc:	A drop event.
				type:	QDropEvent
		"""

		data = drag_and_drop.receive(e)
		if data[u'type'] == u'item-new':
			self.drop_event_item_new(data, e)
		elif data[u'type'] == u'item-existing':
			self.drop_event_item_move(data, e)
		elif data[u'type'] == u'url-local':
			self.main_window.open_file(path=data[u'url'])
			e.accept()
		else:
			e.ignore()
		self.end_drag()

	def dragEnterEvent(self, e):

		"""
		desc:
			Handles drag-enter events to see if the item tree can handle
			incoming drops.

		arguments:
			e:
				desc:	A drag-enter event.
				type:	QDragEnterEvent
		"""

		data = drag_and_drop.receive(e)
		if drag_and_drop.matches(data, [u'item-new', u'item-existing',
			u'url-local']):
			e.accept()
		else:
			e.ignore()

	def dragLeaveEvent(self, e):

		"""
		desc:
			Cancels the drop indicator when a drag leaves.

		arguments:
			e:
				desc:	A drag-move event.
				type:	QDragLeaveEvent
		"""

		self.end_drag()

	def dragMoveEvent(self, e):

		"""
		desc:
			Handles drag-move events to see if the item tree can handle
			incoming drops.

		arguments:
			e:
				desc:	A drag-move event.
				type:	QDragMoveEvent
		"""

		data = drag_and_drop.receive(e)
		self.drop_indicator = None
		if drag_and_drop.matches(data, [u'url-local']):
			e.accept()
			self.end_drag()
			return
		if not drag_and_drop.matches(data, [u'item-new', u'item-existing']):
			e.accept()
			self.end_drag()
			return
		target = self.itemAt(e.pos())
		if not self.droppable(target, data):
			self.end_drag()
			e.ignore()
			return
		e.accept()
		# Update the drop indicator
		index = self.indexFromItem(target)
		rect = self.visualRect(index)
		if target.name == u'__unused__' or ( \
			target.item.name in self.experiment.items.used() and \
			target.item.item_type in (u'loop', u'sequence') and \
			target.item.name != self.experiment.start and \
			target.parent() is not None):
			self.drop_indicator = rect
		else:
			self.drop_indicator = QtCore.QRect(rect.left(), rect.bottom(),
				rect.width(), 0)
		self.viewport().update()

	def paintEvent(self, e):

		"""
		desc:
			A custom pain event for the drop_indicator.

		arguments:
			e:
				type:	QPaintEvent
		"""

		painter = QtGui.QPainter(self.viewport())
		self.drawTree(painter, e.region())
		if self.drop_indicator is not None:
			painter.setPen(self.drop_indicator_pen)
			if self.drop_indicator.height() == 0:
				painter.drawLine(self.drop_indicator.topLeft(),
					self.drop_indicator.topRight())
			else:
				painter.drawRect(self.drop_indicator)

	def contextMenuEvent(self, e):

		"""
		desc:
			Asks a tree item to show a context menu.

		arguments:
			e:
				type:	QContextMenuEvent
		"""

		item = self.itemAt(e.pos())
		if item != None:
			item.show_context_menu(e.globalPos())

	def keyPressEvent(self, e):

		"""
		Capture key presses to auto-activate selected items

		Arguments:
		e -- a QKeyEvent
		"""

		if self.currentItem() == None:
			return
		super(tree_overview, self).keyPressEvent(e)
		if e.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down,
			QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown, QtCore.Qt.Key_Home,
			QtCore.Qt.Key_End, QtCore.Qt.Key_Return]:
			if self.overview_mode:
				self.currentItem().open_tab()

	def recursive_children(self, item):

		"""
		Get a list of unused items from the itemtree

		Returns:
		A list of items (strings) that are children of the parent item
		"""

		children = []
		for i in range(item.childCount()):
			child = item.child(i)
			children.append(unicode(child.text(0)))
			children += self.recursive_children(child)
		return children

	def unused_items(self):

		"""
		Get a list of unused items

		Returns:
		A list of unused items (names as strings)
		"""

		return self.main_window.ui.itemtree.recursive_children( \
			self.main_window.ui.itemtree.topLevelItem( \
				self.main_window.ui.itemtree.topLevelItemCount()-1))

	def rename(self, from_name, to_name):

		"""
		desc:
			Renames an item.

		arguments:
			from_name:
				desc:	The old name.
				type:	unicode
			to_name:
				desc:	The new name.
				type:	unicode
		"""

		self.itemChanged.disconnect()
		for i in range(self.topLevelItemCount()):
			self.topLevelItem(i).rename(from_name, to_name)
		self.itemChanged.connect(self.text_edited)

	def set_icon(self, name, icon):

		"""
		desc:
			Changes an item's icon.

		arguments:
			name:
				desc:	The item name.
				type:	unicode
			icon:
				desc:	The icon name.
				type:	unicode
		"""

		self.itemChanged.disconnect()
		for i in range(self.topLevelItemCount()):
			self.topLevelItem(i).set_icon(name, icon)
		self.itemChanged.connect(self.text_edited)

	def start_edit_runif(self):

		"""
		desc:
			Edits the run-if statement. This is not applicable in overview mode.
		"""

		if self.overview_mode:
			return
		target_treeitem = self.currentItem()
		if target_treeitem == None:
			return
		if target_treeitem.parent() == None:
			# The top-level item is the sequence itself, which doesn't have a
			# run-if statement.
			return
		self.editItem(target_treeitem, 1)

	def start_rename(self):

		"""
		desc:
			Edits the item name.
		"""

		target_treeitem = self.currentItem()
		if target_treeitem != None:
			self.editItem(target_treeitem, 0)

	def setup(self, main_window):

		"""
		desc:
			This function needs to be overridden so that the append button is
			also set up.
		"""

		super(tree_overview, self).setup(main_window)
		if self.append_button is not None:
			self.append_button.setup(main_window)

	def clear(self):

		"""
		desc:
			If the tree is cleared, we need to unset the target tree item in the
			append menu (if any).
		"""

		super(tree_overview, self).clear()
		if self.append_button is None:
			return
		self.append_button.append_menu.target_treeitem = None
