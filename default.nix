{ lib, newScope, fetchFromGitHub }:

lib.makeScope newScope (self: {
  src = fetchFromGitHub {
    owner = "frida";
    repo = "frida";
    rev = "16.1.6";
    hash = "sha256-LLrcJ04wcn6CQ/8NzLdAz6LWyc/jaQgj67bIscMMtMA=";
    fetchSubmodules = true;
  };
})
