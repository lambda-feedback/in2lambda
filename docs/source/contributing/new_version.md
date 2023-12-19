# Publishing a New Version

Congratulations on adding new features and fixing bugs! Here's how a project member can publish a new version:

1) Update the version number in [`pyproject.toml`](https://github.com/lambda-feedback/in2lambda/blob/main/pyproject.toml), which should be near the top of the file:

```toml
[tool.poetry]
name = "in2lambda"
version = "0.2.1"  # <-- This line here
```

2) Create a new [tag](https://git-scm.com/book/en/v2/Git-Basics-Tagging) for the docker image to be built. For instance, to tag a version v1.2.3:

```shell
$ git tag -a v1.2.3 -m "v1.2.3"
$ git push origin v1.2.3
```

3) When one of the PyPi in2lambda maintainers is happy, they can update the package:

```shell
$ poetry build
$ poetry publish
```

4) Celebrate the new release! 🎉
