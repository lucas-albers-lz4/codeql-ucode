const methods = {
  probe: {
    call: function(payload) {
      function popen(s) { return s; }
      return popen(`echo ${payload.args.value} done`);
    }
  }
};
return { probe: methods };
