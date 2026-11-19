import { popen } from 'fs';
function unsupported_subscript() {
  const fd = popen('printf harmless');
  fd['close']();
  fd.read('all');
}
