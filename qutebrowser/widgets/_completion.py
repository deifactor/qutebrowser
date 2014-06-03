# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Completion view for statusbar command section.

Defines a CompletionView which uses CompletionFiterModel and CompletionModel
subclasses to provide completions.
"""

from PyQt5.QtWidgets import QStyle, QTreeView, QSizePolicy
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QItemSelectionModel

import qutebrowser.config.config as config
import qutebrowser.commands.utils as cmdutils
from qutebrowser.widgets._completiondelegate import CompletionItemDelegate
from qutebrowser.config.style import set_register_stylesheet
from qutebrowser.utils.log import completion as logger
from qutebrowser.utils.completer import Completer


class CompletionView(QTreeView):

    """The view showing available completions.

    Based on QTreeView but heavily customized so root elements show as category
    headers, and children show as flat list.

    Highlights completions based on marks in the ROLE_MARKS data.

    Class attributes:
        STYLESHEET: The stylesheet template for the CompletionView.
        COLUMN_WIDTHS: A list of column widths, in percent.

    Attributes:
        completer: The Completer instance to use.
        _ignore_change: Whether to ignore the next completion update.
        _model: The currently active filter model.
        _lastmodel: The model set in the last iteration.
        _enabled: Whether showing the CompletionView is enabled.
        _height: The height to use for the CompletionView.
        _height_perc: Either None or a percentage if height should be relative.
        _delegate: The item delegate used.

    Signals:
        change_completed_part: Text which should be substituted for the word
                               we're currently completing.
                               arg 0: The text to change to.
                               arg 1: True if the text should be set
                                      immediately, without continuing
                                      completing the current field.
        resize_completion: Emitted when the completion should be resized.
    """

    STYLESHEET = """
        QTreeView {{
            {font[completion]}
            {color[completion.bg]}
            outline: 0;
        }}

        QTreeView::item:enabled {{
            {color[completion.item.fg]}
            {color[completion.item.bg]}
        }}

        QTreeView::item:disabled {{
            {color[completion.category.fg]}
            {color[completion.category.bg]}
            border-top: 1px solid {color[completion.category.border.top]};
            border-bottom: 1px solid
                {color[completion.category.border.bottom]};
        }}

        QTreeView::item:selected {{
            border-top: 1px solid {color[completion.item.selected.border.top]};
            border-bottom: 1px solid
                {color[completion.item.selected.border.bottom]};
            {color[completion.item.selected.bg]}
            {color[completion.item.selected.fg]}
        }}
    """
    COLUMN_WIDTHS = [20, 70, 10]

    # FIXME style scrollbar

    change_completed_part = pyqtSignal(str, bool)
    resize_completion = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = Completer(self)
        self._enabled = config.get('completion', 'show')
        self._ignore_change = False
        self._model = None
        self._lastmodel = None

        self._delegate = CompletionItemDelegate(self)
        self.setItemDelegate(self._delegate)
        set_register_stylesheet(self)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.setHeaderHidden(True)
        self.setIndentation(0)
        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # QTBUG? This is a workaround for weird race conditions with invalid
        # item indexes leading to segfaults in Qt.
        #
        # Some background: http://bugs.quassel-irc.org/issues/663
        # The proposed fix there was later reverted because it didn't help.
        self.setUniformRowHeights(True)
        self.hide()
        # FIXME set elidemode

    def _resize_columns(self):
        """Resize the completion columns based on COLUMN_WIDTHS."""
        width = self.size().width()
        pixel_widths = [(width * perc // 100) for perc in self.COLUMN_WIDTHS]
        if self.verticalScrollBar().isVisible():
            pixel_widths[-1] -= self.style().pixelMetric(
                QStyle.PM_ScrollBarExtent) + 5
        for i, w in enumerate(pixel_widths):
            self.setColumnWidth(i, w)

    def _next_idx(self, upwards):
        """Get the previous/next QModelIndex displayed in the view.

        Used by tab_handler.

        Args:
            upwards: Get previous item, not next.

        Return:
            A QModelIndex.
        """
        idx = self.selectionModel().currentIndex()
        if not idx.isValid():
            # No item selected yet
            return self._model.first_item()
        while True:
            idx = self.indexAbove(idx) if upwards else self.indexBelow(idx)
            # wrap around if we arrived at beginning/end
            if not idx.isValid() and upwards:
                return self._model.last_item()
            elif not idx.isValid() and not upwards:
                idx = self._model.first_item()
                self.scrollTo(idx.parent())
                return idx
            elif idx.parent().isValid():
                # Item is a real item, not a category header -> success
                return idx

    def _next_prev_item(self, prev):
        """Handle a tab press for the CompletionView.

        Select the previous/next item and write the new text to the
        statusbar.

        Args:
            prev: True for prev item, False for next one.
        """
        if not self.isVisible():
            # No completion running at the moment, ignore keypress
            return
        idx = self._next_idx(prev)
        self.selectionModel().setCurrentIndex(
            idx, QItemSelectionModel.ClearAndSelect |
            QItemSelectionModel.Rows)

    def set_model(self, model):
        """Switch completion to a new model.

        Called from on_update_completion().

        Args:
            model: The model to use.
        """
        logger.debug("Setting model to {}".format(model.__class__.__name__))
        self.setModel(model)
        self._model = model
        self.expandAll()
        self._resize_columns()
        self._model.rowsRemoved.connect(self.resize_completion)
        self._model.rowsInserted.connect(self.resize_completion)
        self.resize_completion.emit()

    @pyqtSlot(str, str)
    def on_config_changed(self, section, option):
        """Update self._enabled when the config changed."""
        if section == 'completion' and option == 'show':
            self._enabled = config.get('completion', 'show')
        elif section == 'aliases':
            self._init_command_completion()

    @pyqtSlot(str, list, int)
    def on_update_completion(self, prefix, parts, cursor_part):
        """Check if completions are available and activate them.

        Slot for the textChanged signal of the statusbar command widget.

        Args:
            text: The new text
            cursor_part: The part the cursor is currently over.
        """
        if self._ignore_change:
            logger.debug("Ignoring completion update")
            return

        logger.debug("Updating completion, parts: {}, cursor_part {}".format(
            parts, cursor_part))

        if prefix != ':':
            # This is a search or gibberish, so we don't need to complete
            # anything (yet)
            # FIXME complete searchs
            self.hide()
            return

        model = self.completer._get_new_completion(parts, cursor_part)
        if model is None:
            logger.debug("No completion model for {}.".format(parts))
        else:
            logger.debug("New completion: {} / last: {}".format(
                model.srcmodel.__class__.__name__,
                self._lastmodel.srcmodel.__class__.__name__ if self._lastmodel
                is not None else "None"))
        if model != self._lastmodel:
            self._lastmodel = model
            if model is None:
                self.hide()
                return
            self.set_model(model)

        if model is None:
            return

        pattern = parts[cursor_part] if parts else ''
        logger.debug("pattern: {}".format(pattern))
        self._model.pattern = pattern

        if self._model.item_count == 0:
            self.hide()
            return

        self._model.mark_all_items(pattern)
        if self._enabled:
            self.show()

    @pyqtSlot()
    def on_clear_completion_selection(self):
        """Clear the selection model when an item is activated."""
        selmod = self.selectionModel()
        if selmod is not None:
            selmod.clearSelection()
            selmod.clearCurrentIndex()

    @cmdutils.register(instance='mainwindow.completion', hide=True,
                       modes=['command'])
    def completion_item_prev(self):
        """Select the previous completion item."""
        self._next_prev_item(prev=True)

    @cmdutils.register(instance='mainwindow.completion', hide=True,
                       modes=['command'])
    def completion_item_next(self):
        """Select the next completion item."""
        self._next_prev_item(prev=False)

    def selectionChanged(self, selected, deselected):
        """Extend selectionChanged to emit change_completed_part if necessary.

        Args:
            selected: New selection.
            delected: Previous selection.

        Emit:
            change_completed_part: Emitted when there's data for the new item.
        """
        indexes = selected.indexes()
        if indexes:
            data = self._model.data(indexes[0])
            if data is not None:
                if self._model.item_count == 1 and config.get(
                        'completion', 'quick-complete'):
                    # If we only have one item, we want to apply it immediately
                    # and go on to the next part.
                    self.change_completed_part.emit(data, True)
                else:
                    self._ignore_change = True
                    self.change_completed_part.emit(data, False)
                    self._ignore_change = False
        super().selectionChanged(selected, deselected)

    def resizeEvent(self, e):
        """Extend resizeEvent to adjust column size."""
        super().resizeEvent(e)
        self._resize_columns()
