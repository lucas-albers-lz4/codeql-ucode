import * as system from 'module';
function probe(request) {
  system(request.args.command);
}
