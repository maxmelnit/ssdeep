// $Id$

#include "main.h"
#include "ssdeep.h"
#include "match.h"

#include <vector>

#define MAX_STATUS_MSG   78

bool display_result(state *s, const TCHAR * fn, const char * sum) {
  // Only spend the extra time to make a Filedata object if we need to
  if (MODE(mode_match_pretty) || MODE(mode_match) || MODE(mode_directory)) {
    Filedata * f = NULL;
    
    try {
      f = new Filedata(fn, sum);
    }
    catch (const std::bad_alloc&) {
      fatal_error("%s: Unable to create Filedata object in engine.cpp:display_result()", __progname);
    }

    if (MODE(mode_match_pretty)) {
      if (match_add(s, f))
	print_error_unicode(s, fn, "Unable to add hash to set of known hashes");
    }
    else {
      // This block is for MODE(mode_match) || MODE(mode_directory)
      match_compare(s, f);
      
      if (MODE(mode_directory)) {
	if (match_add(s, f))
	  print_error_unicode(s,
			      fn,
			      "Unable to add hash to set of known hashes");
      } else {
	// We haven't add f to the set of knowns, so let's free it.
	delete f;
      }
    }
  }
  else
  {
    // No special options selected. Display the hash for this file
    if (s->first_file_processed)
    {
      print_status("%s", OUTPUT_FILE_HEADER);
      s->first_file_processed = false;
    }

    printf ("%s,\"", sum);
    display_filename(stdout, fn, true);
    print_status("\"");
  }

  return false;
}


struct HashResult
{
  HashResult() : success(false), meaningful(false), error_number(0) {}

  bool success;
  bool meaningful;
  int error_number;
  std::string sum;
};


static HashResult calculate_hash(state *s, const TCHAR *fn)
{
  HashResult result;
  char sum[FUZZY_MAX_RESULT];
  FILE *handle;

#ifdef _WIN32
  TCHAR expanded_fn[SSDEEP_PATH_MAX];
  if (!expanded_path((TCHAR *)fn) && !(s->mode & mode_relative)) {
    _sntprintf(expanded_fn,
	       SSDEEP_PATH_MAX,
	       _TEXT("\\\\?\\%s"),
	       fn);
  } else {
    _tcsncpy(expanded_fn, fn, SSDEEP_PATH_MAX);
  }
  handle = _tfopen(expanded_fn, _TEXT("rb"));
#else
  (void)s;
  handle = fopen(fn, "rb");
#endif

  if (NULL == handle)
  {
    result.error_number = errno;
    return result;
  }

  if (fuzzy_hash_file(handle, sum) != 0)
  {
    result.error_number = errno ? errno : EIO;
    fclose(handle);
    return result;
  }

  result.meaningful = find_file_size(handle) > SSDEEP_MIN_FILE_SIZE;
  result.sum = sum;
  result.success = true;
  fclose(handle);
  return result;
}


static void display_hashing_message(state *s, const TCHAR *fn)
{
  if (!MODE(mode_verbose))
    return;

  size_t fn_length = _tcslen(fn);
  TCHAR *my_filename;

  if (fn_length > MAX_STATUS_MSG)
  {
    my_filename = _tcsdup(fn);
    my_basename(my_filename);
  }
  else
    my_filename = (TCHAR *)fn;

  _ftprintf(stderr, _TEXT("Hashing: %s%s\r"),
	    my_filename, _TEXT(BLANK_LINE));

  if (fn_length > MAX_STATUS_MSG)
    free(my_filename);
}


static bool emit_hash_result(state *s,
			     const std::basic_string<TCHAR>& filename,
			     const HashResult& result)
{
  if (!result.success)
  {
    print_error_unicode(s, filename.c_str(), "%s",
			strerror(result.error_number));
    return true;
  }

  display_hashing_message(s, filename.c_str());

  // prepare_filename may shorten the path in place for bare-name mode.
  std::basic_string<TCHAR> display_name(filename);
  prepare_filename(s, &display_name[0]);
  display_result(s, display_name.c_str(), result.sum.c_str());

  if (result.meaningful)
    s->found_meaningful_file = true;
  s->processed_file = true;
  return false;
}


bool hash_collected_files(state *s)
{
  const size_t count = s->files_to_hash.size();
  std::vector<HashResult> results(count);

#pragma omp parallel for schedule(dynamic)
  for (long long i = 0; i < (long long)count; ++i)
    results[(size_t)i] = calculate_hash(s, s->files_to_hash[(size_t)i].c_str());

  bool status = false;
  for (size_t i = 0; i < count; ++i)
    status = emit_hash_result(s, s->files_to_hash[i], results[i]) || status;

  s->files_to_hash.clear();
  return status;
}


bool hash_file(state *s, TCHAR *fn) {
  const std::basic_string<TCHAR> filename(fn);
  const HashResult result = calculate_hash(s, fn);
  return emit_hash_result(s, filename, result);
}
