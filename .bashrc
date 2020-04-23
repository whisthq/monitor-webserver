# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# Fractal environment variables
export ADMIN_PASSWORD='!!fractal-admin-password!!'
export AZURE_CLIENT_ID='b8823145-362d-4796-90ff-ea185161145d'
export AZURE_CLIENT_SECRET='NWt-1@7?uEjM/3QNN34AbXV_R45l1jin'
export AZURE_SUBSCRIPTION_ID='a813e13b-7199-41ab-8812-e6a3caf764d0'
export AZURE_TENANT_ID='497f0f14-93c3-46f4-b636-de61e2240a84'
export DATABASE_URL='postgres://u97uj1m5q16qjm:pde86ce23ddf2bfa972db8c5d09e12968022c048011d97b5acd4f9fb3a2dda891@ec2-52-205-72-163.compute-1.amazonaws.com:5432/d4lf18ud6qj6nr'
export EMAIL_ADDRESS='ming@fractalcomputers.com'
export EMAIL_PASSWORD='Jiajia98!'
export HEROKU_POSTGRESQL_BLUE_URL='postgres://u97uj1m5q16qjm:pde86ce23ddf2bfa972db8c5d09e12968022c048011d97b5acd4f9fb3a2dda891@ec2-52-205-72-163.compute-1.amazonaws.com:5432/d4lf18ud6qj6nr'
export HEROKU_POSTGRESQL_MAUVE_URL='postgres://vgjpuoqiipwhyo:71a5204e598c343aad3324ad9f5dc31c87aae87761c89a0493e224769ecdd3dc@ec2-174-129-18-42.compute-1.amazonaws.com:5432/dean23lqt7jq3l'
export HEROKU_REDIS_SILVER_URL='redis://h:p126c0ce43dff9b131f83debdb309e66c1f89082229fe10dbaa5170f4c64d84e4@ec2-34-226-228-247.compute-1.amazonaws.com:14059'
export JWT_SECRET_KEY='KLJSAD98klaa!!.ljdSADL87943??as;uf()*^$#cC'
export LOCATION='eastus'
export PLAN_ID='plan_GwV769WQdZOUJR'
export REDIS_URL='redis://h:p126c0ce43dff9b131f83debdb309e66c1f89082229fe10dbaa5170f4c64d84e4@ec2-34-226-228-247.compute-1.amazonaws.com:14059'
export SECRET_KEY='philis@littlec@n@di@n6969'
export STRIPE_SECRET='sk_test_6ndCgv5edtzMuyqMoBbt1gXj00xy90yd4L'
export VM_GROUP='Fractal'
export VM_PASSWORD='password1234567.'
export SENDGRID_API_KEY='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'