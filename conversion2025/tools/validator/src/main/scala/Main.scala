import cats.effect._
import org.http4s._
import org.http4s.dsl.io._
import org.http4s.ember.server.EmberServerBuilder
import org.http4s.server.Router
import com.comcast.ip4s.{Host, Port}

object Main extends IOApp {

  val mathRoutes = HttpRoutes.of[IO] {
    case req @ POST -> Root / "process" =>
      req.as[String].flatMap { input =>
        val cleaned = input.trim.reverse // Example logic
        Ok(s"Processed: $cleaned")
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
