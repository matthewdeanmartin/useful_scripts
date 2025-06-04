#!/bin/bash
cp /hosthome/.ssh/* ~/.ssh
chmod 400 ~/.ssh/*.pem
echo
echo "Available hosts. Connect with \`ssh hostname\`"
echo
grep -P "^Host ([^*]+)$" $HOME/.ssh/config | sed 's/Host //'