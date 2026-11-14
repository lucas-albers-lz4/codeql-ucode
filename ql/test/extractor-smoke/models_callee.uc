import { popen } from 'fs';

function probe(request) {
  popen(request.args.command);
  system(request.args.command);
  popen.read(request.args.command);
  system.foo(request.args.command);
  other.popen(request.args.command);
}
