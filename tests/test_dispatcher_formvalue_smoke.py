"""Offline negative controls for the source and extracted entity oracle."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dispatcher_smoke', ROOT / 'scripts/dispatcher-formvalue-smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class DispatcherObserverOracleTest(unittest.TestCase):
    def test_pinned_source_and_tamper(self):
        data = (smoke.FIXTURE / 'dispatcher.uc').read_bytes()
        smoke.verify_source(data)
        with self.assertRaises(ValueError):
            smoke.verify_source(data + b'\n')

    def test_duplicate_routing_rejected(self):
        stage = Path('/tmp/stage')
        dest = stage / 'usr/share/ucode/luci'
        decisions = [{'path': str(dest / n), 'installed_path': str(Path('usr/share/ucode/luci') / n),
                      'classification': 'plain', 'status': 'plain_route_selected', 'reason': 'ucode_extension'}
                     for n in ('dispatcher.uc', 'controls.uc', 'unrelated.uc')]
        receipt = {'decisions': decisions, 'input_count': 3, 'plain_count': 3,
                   'excluded_count': 0, 'uncertain_count': 0}
        smoke.verify_routing(receipt, stage, dest)
        receipt['decisions'] = decisions + [decisions[0]]
        with self.assertRaises(ValueError):
            smoke.verify_routing(receipt, stage, dest)

    def test_entity_identity_and_exact_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp).resolve()
            dest = stage / 'usr/share/ucode/luci'
            dest.mkdir(parents=True)
            for name in ('dispatcher.uc', 'controls.uc'):
                shutil.copyfile(smoke.FIXTURE / name, dest / name)
            shapes = {533: ('SubscriptExpression', 'none'), 537: ('SubscriptExpression', 'True'),
                      699: ('Identifier', 'none'), 720: ('String', 'none'),
                      935: ('String', 'none'), 936: ('String', 'none')}
            rows = []
            for name, sites in [('dispatcher.uc', shapes), ('controls.uc', {1: ('String', 'none')})]:
                path = dest / name
                lines = path.read_text().splitlines()
                for number, (arg0, arg1) in sites.items():
                    line = lines[number - 1]
                    start = line.index('http.formvalue(')
                    end = line.index(')', start) + 1
                    url = {'uri': path.as_uri(), 'startLine': number, 'startColumn': start + 1,
                           'endLine': number, 'endColumn': end}
                    arity = 1 if arg1 == 'none' else 2
                    rows.append([{'url': url}, f'direct formvalue at {name}:{number}:{arg0}:{arg1}:{arity}'])
            smoke.verify_rows(rows, stage)
            for replacement in (None, {'url': {**rows[0][0]['url'], 'uri': (dest / 'wrong.uc').as_uri()}},
                                {'url': {**rows[0][0]['url'], 'startLine': 1}}):
                altered = [[replacement, rows[0][1]]] + rows[1:]
                with self.assertRaises(ValueError):
                    smoke.verify_rows(altered, stage)
            for bad in (rows[:-1], rows + [rows[0]],
                        [[rows[0][0], rows[0][1][:-1] + '3']] + rows[1:]):
                with self.assertRaises(ValueError):
                    smoke.verify_rows(bad, stage)


if __name__ == '__main__':
    unittest.main()
