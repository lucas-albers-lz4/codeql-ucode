import { popen } from 'fs';

function copied_then_reassigned(other) {
  let fd = popen('printf harmless');
  let alias = fd;
  alias.read('before');
  alias = other;
  alias.close();
}

function reassigned_before_use(other) {
  let fd = popen('printf harmless');
  let alias = fd;
  alias = other;
  alias.read('after');
}

function direct_use() {
  let fd = popen('printf harmless');
  fd.close();
}

function shadowed(other) {
  let fd = popen('printf harmless');
  let alias = fd;
  function inner(alias) { alias.read('shadow'); }
  inner(other);
  alias.read('outer copy');
}

function unrelated(alias) {
  alias.read('unrelated');
  let other = {};
  other.close();
}

function computed_property(key) {
  let fd = popen('printf harmless');
  let alias = fd;
  alias['read']('computed literal');
  alias[key]('computed variable');
  alias.read('direct property');
}
