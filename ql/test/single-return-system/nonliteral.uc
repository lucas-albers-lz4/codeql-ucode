const methods = {
  setBlockDetect: { call: function(request) {
    return { result: system(request.command) == 0 };
  } }
};
return { luci: methods };
