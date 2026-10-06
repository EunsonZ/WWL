args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2) stop("usage: Rscript prepare_data.R table_two_final.dta output.csv")
expected <- "4114a0c1120e6a5cf1e7a2e1f790f04c8d1678bc4e41bd2a901a088affae9db6"
hash_line <- system2("shasum", c("-a", "256", args[1]), stdout=TRUE, stderr=TRUE)
if (!is.null(attr(hash_line, "status")) || length(hash_line) < 1) stop("cannot compute DTA SHA-256 with shasum")
actual <- strsplit(hash_line[1], "[[:space:]]+")[[1]][1]
if (!identical(actual, expected)) stop(sprintf("DTA SHA-256 mismatch: %s", actual))
if (!requireNamespace("foreign", quietly=TRUE)) stop("R package 'foreign' is required; do not auto-install it")
x <- foreign::read.dta(args[1], convert.factors=FALSE)
keep <- !is.na(x$use) & x$use == 1
x <- x[keep, c("difdemshare","demsharenext","right","demshareprev","demwinprev","demofficeexp","othofficeexp","demelectexp","othelectexp","statedisdec")]
if (nrow(x) != 6559) stop(sprintf("unexpected use sample size: %d", nrow(x)))
undefined <- is.na(x$right)
if (sum(undefined) != 1 || !isTRUE(x$difdemshare[undefined] == 0)) stop("undefined treatment must be the unique exact-zero row")
if (any(is.na(x$difdemshare)) || any(is.na(x$demsharenext))) stop("running variable/outcome missing in use sample")
if (any(x$right[!undefined] != as.numeric(x$difdemshare[!undefined] > 0))) stop("right label disagrees with running-variable sign")
write.csv(x, args[2], row.names=FALSE, na="")
csv_line <- system2("shasum", c("-a", "256", args[2]), stdout=TRUE, stderr=TRUE)
if (!is.null(attr(csv_line, "status")) || length(csv_line) < 1) stop("cannot compute CSV SHA-256 with shasum")
csv_sha <- strsplit(csv_line[1], "[[:space:]]+")[[1]][1]
proof <- c(paste0("dta_sha256=", actual), "dta_sha256_verified=true", paste0("csv_sha256=", csv_sha), paste0("rows_use=", nrow(x)))
writeLines(proof, paste0(args[2], ".provenance"))
