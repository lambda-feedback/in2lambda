{-# LANGUAGE OverloadedStrings #-}

module Main where

import Text.Pandoc
-- import Text.Pandoc.Class (runIOorExplode)
-- import Text.Pandoc.Options
-- import Text.Pandoc.Definition (Block(..), Inline(..), MathType(..))
import qualified Data.Text.IO as TIO
import qualified Data.Text as T
import Control.Monad.RWS (MonadReader(reader))

main :: IO ()
main = do
  rawInput <- TIO.getContents
  let readerOpts = def {
        readerExtensions = enableExtension Ext_tex_math_dollars (readerExtensions def)
      }

  (Pandoc _ blocks) <- runIOorExplode $ readMarkdown readerOpts rawInput

  let mathBlocks = findMath blocks
  let rawLineErrors = checkRawMathRules rawInput

  putStrLn "🔍 Math blocks found:"
  mapM_ print mathBlocks

  if null rawLineErrors
    then putStrLn "✅ Lexdown math formatting looks valid"
    else do
      putStrLn "❌ Lexdown math formatting issues:"
      mapM_ putStrLn rawLineErrors

-- 🔍 Extract inline and display math blocks
findMath :: [Block] -> [Inline]
findMath = concatMap getInlinesFromBlock
  where
    getInlinesFromBlock :: Block -> [Inline]
    getInlinesFromBlock (Para inls) = filter isMath inls
    getInlinesFromBlock (Plain inls) = filter isMath inls
    getInlinesFromBlock _ = []

    isMath :: Inline -> Bool
    isMath (Math _ _) = True
    isMath _ = False

-- 🧪 Custom Lexdown formatting rules (raw line analysis)
checkRawMathRules :: T.Text -> [String]
checkRawMathRules input =
  let ls = zip [1 :: Int ..] (T.lines input)
  in concatMap checkLine ls
  where
    checkLine (i, l)
      | "$$" `T.isInfixOf` l && T.strip l /= "$$" =
          ["Line " ++ show i ++ ": ❌ `$$` must be alone on its own line."]
      | "$" `T.count` l == 1 =
          ["Line " ++ show i ++ ": ❌ unmatched `$` symbol."]
      | otherwise = []