using System.Data.SQLite;
using CommandLine;

// Parse command-line arguments
Parser.Default.ParseArguments<Options>(args)
    .WithParsed(opts => RunOptionsAndReturnExitCode(opts))
    .WithNotParsed(errs => HandleParseError(errs));

// Method to handle parsed options
void RunOptionsAndReturnExitCode(Options opts)
{
    try
    {
        if (!File.Exists(opts.Db))
        {
            throw new FileNotFoundException($"Database {opts.Db} not found");
        }

#pragma warning disable CS8604 // Possible null reference argument.
        using (StreamReader? sr = new(path: opts.File))
        using (SQLiteConnection? conn = new($"Data Source={opts.Db};Version=3;"))
        {
            conn.Open();
            SQLiteCommand? cmd = new(conn);
            if (!opts.Verbose)
            {
                Console.WriteLine($"Adding FormIDs from {opts.File} to {opts.Table}");
            }

            string? line;
            while ((line = sr.ReadLine()) != null)
            {
                line = line.Trim();
                if (line.Contains(" | "))
                {
#pragma warning disable CA1861 // Avoid constant arrays as arguments
                    var data = line.Split(separator: new string[] { " | " }, options: StringSplitOptions.None);
#pragma warning restore CA1861 // Avoid constant arrays as arguments
                    if (opts.Verbose)
                    {
                        Console.WriteLine($"Adding {line} to {opts.Table}");
                    }

                    if (data.Length >= 3)
                    {
                        string? plugin = data[0];
                        string? formid = data[1];
                        string? entry = data[2];
                        cmd.CommandText = $"INSERT INTO {opts.Table} (plugin, formid, entry) VALUES (@plugin, @formid, @entry)";
                        cmd.Parameters.AddWithValue("@plugin", plugin);
                        cmd.Parameters.AddWithValue("@formid", formid);
                        cmd.Parameters.AddWithValue("@entry", entry);
                        cmd.ExecuteNonQuery();
                    }
                }
            }

            if (conn.State == System.Data.ConnectionState.Open)
            {
                cmd.CommandText = "VACUUM";
                cmd.ExecuteNonQuery();
                Console.WriteLine("Optimizing database...");
            }
        }
#pragma warning restore CS8604 // Possible null reference argument.
    }
    catch (FileNotFoundException fnfe)
    {
        Console.Error.WriteLine($"File error: {fnfe.Message}");
    }
    catch (SQLiteException sqle)
    {
        Console.Error.WriteLine($"Database error: {sqle.Message}");
    }
    catch (IOException ioe)
    {
        Console.Error.WriteLine($"I/O error: {ioe.Message}");
    }
    catch (ArgumentException ae)
    {
        Console.Error.WriteLine($"Argument error: {ae.Message}");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"An unexpected error occurred: {ex.Message}");
    }
}

// Method to handle parsing errors
void HandleParseError(IEnumerable<Error> errs)
{
    // Handle errors appropriately here, such as displaying a help message
    Console.Error.WriteLine("Error parsing command line arguments.");
}

// Define the options class
class Options
{
    [Value(0, MetaName = "file", HelpText = "The file to add to the database", Default = "FormID_List.txt")]
    public string? File { get; set; }

    [Option('t', "table", HelpText = "The table to add the file to", Default = "Fallout4")]
    public string? Table { get; set; }

    [Option('d', "db", HelpText = "The database to add the file to", Default = "../CLASSIC Data/databases/Fallout4 FormIDs.db")]
    public string? Db { get; set; }

    [Option('v', "verbose", HelpText = "Prints out the lines as they are added", Default = false)]
    public bool Verbose { get; set; }
}