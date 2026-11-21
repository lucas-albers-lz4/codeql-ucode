import { popen } from 'fs';

function direct_copy() {
  let fd = popen('printf harmless');
  let alias = fd;
  let bare = alias.read;
  alias.read('all');
  alias.close();
}

function direct_receiver() {
  let fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}

function unrelated_same_name(other) {
  let alias = other;
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
