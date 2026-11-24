import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      try { fail(); }
      catch (input) { return popen(`echo ${input.args.value} done`); }
    }
  }
};
return { probe: methods };
