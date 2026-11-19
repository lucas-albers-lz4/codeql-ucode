function no_import() {
  const fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}
