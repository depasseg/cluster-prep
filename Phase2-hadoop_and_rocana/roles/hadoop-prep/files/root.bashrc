# .bashrc

# User specific aliases and functions

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
alias reboot='touch /root/reboot; reboot'

# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi


#######
#######
#######

export MANPATH=$MANPATH:/usr/share/man:/usr/local/share:/usr/local/share/man:/usr/local/man
export EDITOR=vi
export PS1="[\$(date +%H:%M)]:[\u@\h:\W]# "
export JAVA_HOME=/usr/java/latest
export HISTSIZE=99999
export HISTFILESIZE=99999
export HISTTIMEFORMAT="%Y-%m-%d %T -> "
export HISTCONTROL=erasedups
export HISTIGNORE="&:ls:l:[bf]g:exit"
export PATH=$JAVA_HOME/bin:$PATH:/usr/local/sbin:/usr/local/bin
shopt -s histappend
set -o histexpand
set -o vi

#
# User specific aliases and functions
#
alias l='ls'
alias ls='ls -hF'
alias la='ls -Alh'              # show hidden files
alias li='ls -li'
alias lx='ls -lXBh'             # sort by extension
alias lk='ls -lSr'              # sort by size
alias lc='ls -lcrh'             # sort by change time
alias lu='ls -lurh'             # sort by access time
alias lr='ls -lRh'              # recursive ls
alias lt='ls -ltrh'             # sort by date
alias ll='ls -lsh'              #
alias lm='ls -alh |more'        # pipe through 'more'
alias tree='tree -Csu'          # nice alternative to 'ls'
alias lsd='ls -lsd'
alias las='ls -lash'
#
alias dfl='df -l'
alias dfh='df -h'
alias dfn='df -t nfs -h'
alias dfi='df -i'
#
alias git="SSH_ASKPASS='' git"


### FUNCTIONS

  function ldl
     {
     # Display directory permissions
     if test $1x = 'x'; then
         ls -l|grep ^d|more
     else
         ls -lsd $1 | more
     fi
     }


  function psg
     {
     if [ -z "$1" ]; then
             ps auxw|more
             return 0
     fi
     ps auxw | grep --color $1 | grep -v grep|more
       return 0
     }

  function psgw
     {
     if [ -z "$1" ]; then
             ps auxwwee|more
             return 0
     fi
     ps auxwwee | grep --color $1 | grep -v grep|more
       return 0
     }

  function psgmore
     {
     if [ -z "$1" ]; then
             ps auxw|more
             return 0
     fi
     ps auxw | grep -v grep|more
       return 0
     }
