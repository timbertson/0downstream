# 0downstream

Easily generate [zero-install][] feeds and keep them up to date based on an
existing upstream project. You can run this feed from:
[http://gfxmonk.net/dist/0install/0downstream.xml][self]

Currently supported project sources are:

 - [github][]
 - [rubygems.org][]
 - [pypi][]

These locations are all frequently used for interpreted languages. There is no
support for `0compile`d (source) feeds yet, but I hope to add it in the future.


### Create a new feed:

    0downstream new --prefix=<prefix> <url> <filename>

e.g:

    0downstream new \
      --prefix=http://gfxmonk.net/dist/0install/ \
      https://github.com/jkbr/httpie \
      httpie.xml

Instead of the URL, you can also just use <type>:<id>, i.e: `github:jkbr/httpie`

This will fill in feed details using the available metadata, and add an
implementation for the latest implementation of the project, based on
project releases (or version tags in the case of github). You'll still
have to fill in dependency information, environment bindings and any
commands yourself, but hopefully only once. You can see the result at
[my 0install repository](http://gfxmonk.net/dist/0install/httpie.xml)
(view source to see the actual generated xml).

The `prefix` argument is the base URL where you plan to upload the feed. All mine
go in `http://gfxmonk.net/dist/0install/`.

### update an existing feed:

because 0downstream embeds project information inside the generated feed, you
can just run:

    0downstream update <filename>

And it'll add an &lt;implementation&gt; for the latest version of the project
(in the &lt;group&gt; nearest the end of the file).

### check for updates:

Not very useful for manual use, but this command will exit with a `1` status
code if there is a newer version on the project page than in the feed. Probably
useful in a `cron` script.

    0downstream check <filename>

# "it doesn't work", or "you should add ..."

Please open a github issue. I especially like the "pull request" type where
you've done all the hard work and I just press the green button.

It should be reasonably easy to add a new project type - you can use one of the
existing ones in `zeroinstall_downstream/project` to base it on. I won't merge
pull requests for new project sources until you've added the appropriate tests
(they're not hard!).

[zero-install]:   http://0install.net/
[github]:         https://github.com/
[rubygems.org]:   https://rubygems.org/
[pypi]:           https://pypi.python.org/pypi/
[self]:           http://gfxmonk.net/dist/0install/0downstream.xml
