import { popen } from 'fs';
function shadowed_factory(popen) {
  const fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}
