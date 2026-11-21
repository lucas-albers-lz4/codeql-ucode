import { popen } from 'fs';

function direct_copy() {
  let fd = popen('printf harmless');
  let alias = fd;
  alias.read('all');
  alias.close();
}

function reassigned_before_use(other) {
  let fd = popen('printf harmless');
  let alias = fd;
  alias = other;
  alias.read('all');
  alias.close();
}

function reassigned_after_use(other) {
  let fd = popen('printf harmless');
  let alias = fd;
  alias.read('all');
  alias = other;
  alias.close();
}
