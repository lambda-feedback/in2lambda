package validator

import cats.effect._
import org.http4s.{parser => _, _}
import org.http4s.dsl.io._
import org.http4s.ember.server.EmberServerBuilder
import org.http4s.server.Router
import com.comcast.ip4s.{Host, Port}

import parser.*
import validator.{validate_markdown, rebuild_markdown}

object Main extends IOApp {

  val mathRoutes = HttpRoutes.of[IO] {
    case req @ POST -> Root / "process" =>
      req.as[String].flatMap { input => 
        parser.parse(input) match {
          case Right(markdown) => 
            if (validate_markdown(markdown)) {
              val cleaned = rebuild_markdown(markdown)
              Ok(s"Processed: $cleaned")
            } else {
              BadRequest("Invalid Markdown: validation failed")
            }
          case Left(error) => 
            BadRequest(s"Parse error: ${error.toString}")
        }
      }
  }

  val httpApp = Router("/" -> mathRoutes).orNotFound

  val host: Host = Host.fromString("localhost").getOrElse(Host.fromString("0.0.0.0").get)
  val port: Port = Port.fromInt(8080).getOrElse(Port.fromInt(80).get)

  // runs the server
  def run(args: List[String]): IO[ExitCode] =
    EmberServerBuilder
      .default[IO]
      .withHost(host)
      .withPort(port)
      .withHttpApp(httpApp)
      .build
      .use(_ => IO.never)
      .as(ExitCode.Success)
}
