"""Test dei controlli di sicurezza di Print Doctor, fuori da OrcaSlicer.

Avvio dalla cartella del progetto:  python3 -m unittest discover tests
Il modulo `orca` esiste solo dentro OrcaSlicer: qui lo sostituisce un finto modulo minimo.
"""
import os
import sys
import types
import unittest

_fake = types.ModuleType("orca")


class _Base:
    pass


_fake.script = types.SimpleNamespace(ScriptPluginCapabilityBase=_Base)
_fake.base = _Base
_fake.plugin = lambda cls: cls
_fake.ExecutionResult = type("ExecutionResult", (), {})
_fake.host = None
sys.modules.setdefault("orca", _fake)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import print_doctor as pd  # noqa: E402


def vals(printer=None, process=None, filament=None):
    return {"printer": printer or {}, "process": process or {}, "filament": filament or {}}


FIL = {"nozzle_temperature_range_low": ["190"], "nozzle_temperature_range_high": ["230"],
       "nozzle_temperature": ["210"], "hot_plate_temp": ["60"], "filament_max_volumetric_speed": ["15"]}
PRN = {"nozzle_diameter": ["0.4"], "retraction_length": ["0.8"], "retraction_speed": ["40"],
       "machine_max_acceleration_x": ["5000", "1000"], "machine_max_acceleration_y": ["5000", "1000"],
       "machine_max_acceleration_extruding": ["4000", "1000"], "machine_max_jerk_x": ["10", "8"],
       "machine_max_speed_x": ["300", "100"], "machine_max_speed_y": ["300", "100"]}
V = vals(PRN, {}, FIL)


def err(ptype, key, value, v=V, base=None):
    return pd.safety_error(ptype, key, value, v, base)


class Numbers(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(pd.numbers("0.2"), [0.2])
        self.assertEqual(pd.numbers("15%"), [15.0])
        self.assertEqual(pd.numbers("200,210;220"), [200.0, 210.0, 220.0])
        self.assertEqual(pd.numbers("nil"), [])
        self.assertIsNone(pd.numbers("abc"))

    def test_machine_limit_uses_normal_mode_only(self):
        # [normale, silenziosa]: conta solo la normale
        self.assertEqual(pd.machine_limit(V, "machine_max_acceleration_x"), 5000)
        self.assertIsNone(pd.machine_limit(vals(), "machine_max_acceleration_x"))
        self.assertIsNone(pd.machine_limit(vals({"machine_max_speed_x": ["0", "0"]}), "machine_max_speed_x"))


class Keys(unittest.TestCase):
    def test_printer_never_changed(self):
        self.assertTrue(err("printer", "nozzle_diameter", "0.6").startswith("FORBIDDEN"))

    def test_gcode_forbidden(self):
        self.assertTrue(err("filament", "filament_start_gcode", "G28").startswith("FORBIDDEN"))

    def test_other_temperatures_forbidden(self):
        self.assertTrue(err("filament", "chamber_temperature", "50").startswith("FORBIDDEN"))

    def test_unknown_or_wrong_preset_is_manual(self):
        self.assertTrue(err("process", "nozzle_temperature", "210").startswith("MANUAL"))
        self.assertTrue(err("process", "made_up_key", "1").startswith("MANUAL"))


class Values(unittest.TestCase):
    def test_types(self):
        self.assertTrue(err("filament", "nozzle_temperature", "abc").startswith("INVALID"))
        self.assertTrue(err("filament", "nozzle_temperature", "220%").startswith("INVALID"))
        self.assertTrue(err("process", "sparse_infill_density", "15").startswith("INVALID"))
        self.assertIsNone(err("process", "sparse_infill_density", "15%"))

    def test_nil_only_where_allowed(self):
        self.assertTrue(err("filament", "nozzle_temperature", "nil").startswith("INVALID"))
        self.assertIsNone(err("filament", "filament_retraction_length", "nil"))


class Temperatures(unittest.TestCase):
    def test_nozzle_inside_filament_range(self):
        self.assertIsNone(err("filament", "nozzle_temperature", "225"))
        self.assertTrue(err("filament", "nozzle_temperature", "240").startswith("UNSAFE"))
        self.assertTrue(err("filament", "nozzle_temperature", "180").startswith("UNSAFE"))

    def test_nozzle_needs_a_range(self):
        v = vals(PRN, {}, {"nozzle_temperature": ["210"]})
        self.assertTrue(err("filament", "nozzle_temperature", "210", v).startswith("FORBIDDEN"))

    def test_bed_at_most_plus_10_from_session_start(self):
        self.assertIsNone(err("filament", "hot_plate_temp", "70"))
        self.assertTrue(err("filament", "hot_plate_temp", "71").startswith("UNSAFE"))
        # dopo un primo +10 non se ne concede un altro: si conta dal valore di partenza
        v = vals(PRN, {}, dict(FIL, hot_plate_temp=["70"]))
        base = {("filament", "hot_plate_temp"): ["60"]}
        self.assertTrue(err("filament", "hot_plate_temp", "80", v, base).startswith("UNSAFE"))
        self.assertIsNone(err("filament", "hot_plate_temp", "65", v, base))

    def test_bed_never_set_to_zero(self):
        # 0 = piatto non supportato, o primo strato su piatto freddo
        self.assertTrue(err("filament", "hot_plate_temp", "0").startswith("UNSAFE"))
        v = vals(PRN, {}, dict(FIL, hot_plate_temp_initial_layer=["60"]))
        self.assertTrue(err("filament", "hot_plate_temp_initial_layer", "0", v).startswith("UNSAFE"))
        # se e gia 0 (piatto non supportato) resta com'e
        v = vals(PRN, {}, dict(FIL, cool_plate_temp=["0"]))
        self.assertIsNone(err("filament", "cool_plate_temp", "0", v))

    def test_bed_never_above_max(self):
        v = vals(PRN, {}, dict(FIL, hot_plate_temp=["115"]))
        self.assertTrue(err("filament", "hot_plate_temp", "125", v).startswith("UNSAFE"))


class Flow(unittest.TestCase):
    def test_flow_ratio(self):
        self.assertIsNone(err("filament", "filament_flow_ratio", "0.95"))
        self.assertTrue(err("filament", "filament_flow_ratio", "1.3").startswith("INVALID"))

    def test_volumetric_speed_plus_10_percent(self):
        self.assertIsNone(err("filament", "filament_max_volumetric_speed", "16.5"))
        self.assertTrue(err("filament", "filament_max_volumetric_speed", "17").startswith("UNSAFE"))
        self.assertIsNone(err("filament", "filament_max_volumetric_speed", "10"))


class Geometry(unittest.TestCase):
    def test_layer_height_against_nozzle(self):
        self.assertIsNone(err("process", "layer_height", "0.28"))
        self.assertTrue(err("process", "layer_height", "0.32").startswith("UNSAFE"))

    def test_line_width_mm_or_percent(self):
        self.assertIsNone(err("process", "line_width", "0.45"))
        self.assertIsNone(err("process", "line_width", "0"))
        self.assertIsNone(err("process", "line_width", "110%"))
        self.assertTrue(err("process", "line_width", "1.5").startswith("UNSAFE"))
        self.assertTrue(err("process", "line_width", "400%").startswith("UNSAFE"))


class Retraction(unittest.TestCase):
    def test_length_capped_by_printer(self):
        # stampante con 0.8 mm: tetto max(2, 0.8*2) = 2 mm
        self.assertIsNone(err("filament", "filament_retraction_length", "1.5"))
        self.assertTrue(err("filament", "filament_retraction_length", "3").startswith("UNSAFE"))

    def test_speed(self):
        self.assertIsNone(err("filament", "filament_retraction_speed", "45"))
        self.assertTrue(err("filament", "filament_retraction_speed", "0").startswith("UNSAFE"))
        self.assertIsNone(err("filament", "filament_deretraction_speed", "0"))      # 0 = come la ritrazione
        self.assertTrue(err("filament", "filament_retraction_speed", "100").startswith("UNSAFE"))


class MachineLimits(unittest.TestCase):
    def test_speed(self):
        self.assertIsNone(err("process", "outer_wall_speed", "250"))
        self.assertTrue(err("process", "outer_wall_speed", "350").startswith("UNSAFE"))

    def test_acceleration(self):
        self.assertIsNone(err("process", "default_acceleration", "3500"))
        self.assertTrue(err("process", "default_acceleration", "4500").startswith("UNSAFE"))

    def test_jerk(self):
        self.assertIsNone(err("process", "outer_wall_jerk", "9"))
        self.assertTrue(err("process", "outer_wall_jerk", "12").startswith("UNSAFE"))

    def test_no_limits_known(self):
        v = vals({"nozzle_diameter": ["0.4"]}, {}, FIL)
        self.assertIsNone(err("process", "outer_wall_speed", "350", v))


if __name__ == "__main__":
    unittest.main()
