using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;

using System;
using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Collections;
using System.Collections.Generic;


public class UnityCallPython : MonoBehaviour
{
    [Tooltip("IP address")]
    public string ip = "127.0.0.1";
    [Tooltip("Port number")]
    public int port = 60000;

    [Tooltip("Scene names")]
    public string loadScene;
    public string startScene;
    public string waitScene;
    public string expScene;
    [Tooltip("Blocking time (sec)")]
    public float maxWaitingTime = 30f;
    public float sceneBlockingTime = 1f;

    public Socket clientSocket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);

    string prevScene = "";
    long startTime;


    private void Awake()
    {
        try
        {
            clientSocket.Connect(new IPEndPoint(IPAddress.Parse(ip), port));
            Debug.Log("Connected!");
            Shock(0, -100); // Test without real shocks.
        }
        catch (Exception)
        {
            Debug.Log("Connection Error!");
        }

        DontDestroyOnLoad(this.gameObject);
    }

    private void Update()
    {
        string currentScene = SceneManager.GetActiveScene().name;
        if (currentScene != prevScene)
        {
            prevScene = currentScene;
            startTime = DateTimeOffset.Now.ToUnixTimeMilliseconds();
        }

        long currentTime = DateTimeOffset.Now.ToUnixTimeMilliseconds();
        if ((currentScene == loadScene) && (currentTime - startTime > sceneBlockingTime * 1000)) 
        {
            SceneManager.LoadScene(startScene);
        }
        if ((currentScene == waitScene) && (currentTime - startTime > sceneBlockingTime * 1000))
        {
            ReceiveTR(maxWaitingTime);
            SceneManager.LoadScene(expScene);
        }
    }

    private void OnApplicationQuit()
    {
        clientSocket.Shutdown(SocketShutdown.Both);
        clientSocket.Close();
    }

    public void Shock(int bodyPart, float shockingDuration)
    {
        SendMessage(bodyPart.ToString(), shockingDuration.ToString());
    }

    public void SendMessage(params string[] argvs)
    {
        string content = "";
        if (argvs != null)
        {
            foreach (string item in argvs)
            {
                content += " " + item;
            }
        }

        try
        {
            byte[] byteData = Encoding.ASCII.GetBytes(content);
            clientSocket.Send(byteData);
        }
        catch (ArgumentNullException ane)
        {
            Console.WriteLine("ArgumentNullException : {0}", ane.ToString());
        }
        catch (SocketException se)
        {
            Console.WriteLine("SocketException : {0}", se.ToString());
        }
        catch (Exception e)
        {
            Console.WriteLine("Unexpected exception : {0}", e.ToString());
        }
    }

    public void ReceiveTR(float maxTime)
    {
        long time = new DateTimeOffset(DateTime.Now).ToUnixTimeSeconds();

        bool TR_flag = false;
        bool TR_first = false; // ignoring the first jammed input

        while (new DateTimeOffset(DateTime.Now).ToUnixTimeSeconds() - time < maxTime)
        {
            // print(new DateTimeOffset(DateTime.Now).ToUnixTimeSeconds() - time);

            // Waiting for TR signal to start the task
            try
            {
                string data = null;
                byte[] bytes = null;
                bytes = new byte[1024];
                int bytesRec = clientSocket.Receive(bytes);
                data = Encoding.ASCII.GetString(bytes, 0, bytesRec);

                if (Int32.Parse(data[data.Length - 1].ToString()) > 0)
                {
                    if (TR_first)
                    {
                        TR_flag = true;
                        break;
                    }
                    TR_first = true;
                }
            }
            catch (Exception e)
            {
                TR_flag = true;
                Debug.Log("TR Retrieval Error!");
                Debug.Log(e);
                break;
            }
            Shock(0, -100); // Test without real shocks.
        }
        if (!TR_flag)
        {
            Debug.Log("TR Retrieval exceeds Tolerance Time!");
        }
    }

}
