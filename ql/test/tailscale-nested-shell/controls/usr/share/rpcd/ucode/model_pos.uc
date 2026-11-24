'use strict';
import { popen } from 'fs';
const methods = {
  probe: {
    call: function(request) {
      popen('/bin/sh -c "' + request.args.cmd + ' &"', 'r');
    }
  }
};
return methods;
