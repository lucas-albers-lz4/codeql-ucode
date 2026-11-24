import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      try { throw { args: { value: 'constant' } }; }
      catch (input) { return popen(`echo ${input.args.value} done`); }
    }
  }
};
return { probe: methods };
