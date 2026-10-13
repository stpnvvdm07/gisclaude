from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, Qgis
from . import core

class KonkovoTools:
    def __init__(self, iface): self.iface = iface; self.actions = []
    def initGui(self):
        for text, fn in (("Обновить слои до последней версии", self.update), ("Удалить ненужные слои", self.clean)):
            a = QAction(text, self.iface.mainWindow()); a.triggered.connect(fn)
            self.iface.addPluginToMenu("Коньково", a); self.actions.append(a)
    def unload(self):
        for a in self.actions: self.iface.removePluginMenu("Коньково", a)
    def _log(self, msgs): QMessageBox.information(self.iface.mainWindow(), "Коньково", "\n".join(msgs[-40:]) or "Нечего менять.")
    def update(self):
        msgs = []; core.update_layers(log=msgs.append); self._log(msgs); self.iface.mapCanvas().refreshAllLayers()
    def clean(self):
        items = core.find_unneeded()
        txt = "\n".join(f"• {l.name()} — {w}" for l, w in items[:40]) or "Ненужных слоёв нет."
        if QMessageBox.question(self.iface.mainWindow(), "Коньково", f"Удалить из проекта?\n\n{txt}\n\nи пустые группы") != QMessageBox.Yes: return
        msgs = []; core.remove_unneeded(log=msgs.append, items=items); self._log(msgs)
        self.iface.messageBar().pushMessage("Коньково", "Проект очищен — сохраните его (Ctrl+S).", Qgis.Info)
