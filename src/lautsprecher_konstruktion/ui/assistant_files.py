"""File, demo, export and expert-window actions of the guided assistant (mixed into AssistantWindow)."""
from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import QUrl
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)

from lautsprecher_konstruktion.appdata import (
    get_logger,
)
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.automatic import (
    SpeakerDesign,
)
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project
from lautsprecher_konstruktion.ui.library_dialog import LibraryDialog
from lautsprecher_konstruktion.ui.main_window import MainWindow

LOG = get_logger("ui")
AUTOSAVE_INTERVAL_MS = 60_000




class FileActionsMixin:
    """Actions that load, save, export or hand the design to the expert editor."""

    def _expert(self) -> None:
        if self.expert_window is None:
            self.expert_window = MainWindow()
            self.expert_window.set_mode(self.mode)
            self.expert_window.projectCalculated.connect(self._expert_updated)
        current = self._current()
        if current:
            self.expert_window._apply_project(current.project)
            self.expert_window.calculate()
        self.expert_window.show()
        self.expert_window.raise_()

    def _expert_updated(self, bundle: DesignBundle) -> None:
        bom = build_bom(bundle)
        design = SpeakerDesign("Expertenentwurf", bundle.project, bundle,
            bundle.project.driver, None, 0, (), ("Im Expertenmodus bearbeitet.",),
            bom, None, None, False, budget_cost(bom))
        self.designs = (design,)
        self._stale = False
        self._unsaved = True
        self.variant_list.clear()
        self.comparison.setRowCount(0)
        self.variant_list.addItem("Expertenentwurf · aktuelle Berechnung")
        self.variant_cards.set_designs(self.designs)
        self._show_start(False)
        project = bundle.project
        loaded_method = "target_curve" if project.target_curve_points or project.target_eq_bands else "classic"
        self.design_method.blockSignals(True)
        self.design_method.setCurrentIndex(self.design_method.findData(loaded_method))
        self.design_method.blockSignals(False)
        self._sync_method_cards()
        self.create_button.setText(
            "Passenden Entwurf zur Zielkurve berechnen"
            if loaded_method == "target_curve" else "Entwurf erstellen"
        )
        if project.target_curve_points or project.target_eq_bands:
            self.target_curve.restore_state(
                project.target_curve_points,
                preset=project.target_curve_preset,
                analysis_mode=project.target_curve_mode,
                bands=project.target_eq_bands,
            )
        self.save_button.setEnabled(True)
        self.variant_list.setCurrentRow(0)
        self._set_state("info", "Expertenentwurf übernommen")

    def _library(self) -> None:
        dialog = LibraryDialog(self.library, self)
        dialog.exec()

    def _demo(self) -> None:
        choice = self.demo_choice.currentIndex()
        if choice == 0:
            return
        presets = {
            1: ("Regallautsprecher", "auto", 230, 420, 310, "neutral", None, None),
            2: ("Subwoofer", "bass_reflex", 400, 600, 600, "deep_bass", None, None),
            3: ("Subwoofer", "sealed", 400, 600, 600, "neutral", None, None),
            4: ("Standlautsprecher", "auto", 340, 950, 450, "neutral", None, None),
            5: ("Subwoofer", "auto", 300, 300, 200, "deep_bass", 20, 120),
        }
        speaker, enclosure, w, h, d, profile, f3, spl = presets[choice]
        self.speaker_type.setCurrentText(speaker)
        self.enclosure.setCurrentIndex(self.enclosure.findData(enclosure))
        self.max_width.setValue(w)
        self.max_height.setValue(h)
        self.max_depth.setValue(d)
        self.max_volume.setValue(0)
        self.profile.setCurrentIndex(self.profile.findData(profile))
        self.options.setChecked(f3 is not None or spl is not None)
        self.target_f3.setValue(f3 or 0)
        self.target_spl.setValue(spl or 0)
        self.project_name.setText(self.demo_choice.currentText()+" · TESTDATEN")

    def _save(self) -> None:
        design = self._current()
        if not design:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Projekt speichern",
            design.project.name+".json", "Lautsprecherprojekt (*.json)")
        if filename:
            try:
                Path(filename).write_text(design.project.model_dump_json(indent=2), encoding="utf-8")
            except OSError as exc:
                LOG.warning("Speichern fehlgeschlagen: %s", exc)
                QMessageBox.warning(self, "Speichern fehlgeschlagen", str(exc))
                return
            self._unsaved = False
            self.autosave.discard()
            self.recent.add(filename)
            self._refresh_recent_menu()
            self.statusBar().showMessage(f"Projekt gespeichert: {filename}")

    def _load(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Projekt laden", "", "Lautsprecherprojekt (*.json)")
        if filename:
            self.open_project_file(filename)

    def open_project_file(self, filename: str | Path, *, remember: bool = True) -> bool:
        """Load and calculate a saved project; returns False and informs the user on failure."""
        if not self._confirm_discard():
            return False
        try:
            project = SpeakerProject.model_validate_json(Path(filename).read_text(encoding="utf-8"))
            bundle = calculate_project(project)
        except (OSError, ValidationError, ValueError) as exc:
            LOG.warning("Projekt laden fehlgeschlagen (%s): %s", filename, exc)
            QMessageBox.warning(self, "Projekt laden fehlgeschlagen", str(exc))
            return False
        self._expert_updated(bundle)
        if remember:
            self._unsaved = False
            self.recent.add(filename)
            self._refresh_recent_menu()
        self.statusBar().showMessage(f"Projekt geladen: {filename}")
        return True

    def _export(self) -> None:
        design = self._current()
        if not design:
            return
        folder = QFileDialog.getExistingDirectory(self, "Exportordner wählen")
        if folder:
            try:
                package = export_project_package(design.bundle, folder,
                    self.cutting_panel.settings(design.project.material))
                self.statusBar().showMessage(f"Fertigungsunterlagen: {package}")
                dialog = QMessageBox(self)
                dialog.setWindowTitle("Fertigungsunterlagen bereit")
                dialog.setIcon(QMessageBox.Icon.Information)
                dialog.setText("Export abgeschlossen")
                dialog.setInformativeText(
                    f"Die Fertigungsunterlagen wurden erstellt.\n{package}"
                )
                open_button = dialog.addButton(
                    "Ordner öffnen", QMessageBox.ButtonRole.ActionRole
                )
                dialog.addButton("Fertig", QMessageBox.ButtonRole.AcceptRole)
                dialog.exec()
                if dialog.clickedButton() is open_button:
                    target = Path(package)
                    QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(target if target.is_dir() else target.parent))
                    )
            except (OSError, ValueError) as exc:
                LOG.warning("Export fehlgeschlagen: %s", exc)
                QMessageBox.warning(self, "Export fehlgeschlagen", str(exc))

    # --- menu, help, recovery -------------------------------------------------
