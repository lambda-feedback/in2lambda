name := "validator"

version := "0.1"

scalaVersion := "3.3.1"

libraryDependencies ++= Seq(
  "org.typelevel" %% "cats-effect" % "3.5.1",
  "org.http4s" %% "http4s-dsl" % "1.0.0-M39",
  "org.http4s" %% "http4s-ember-server" % "1.0.0-M39",
  "ch.qos.logback" % "logback-classic" % "1.4.11",
  "com.github.j-mie6" %% "parsley" % "5.0.0-M9",
  "org.scalameta" %% "munit" % "1.0.0-M11" % Test
)