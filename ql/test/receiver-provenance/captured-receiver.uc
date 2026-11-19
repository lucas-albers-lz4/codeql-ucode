import { popen } from 'fs';
function captured_receiver() {
  const fd = popen('printf harmless');
  function inner() { fd.read('all'); }
  fd.read('all');
  fd.close();
}
